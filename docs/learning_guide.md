# Sentinel-HealOps: Exhaustive Code Explanation Guide

This document is for developers who want to understand exactly how every line of code in the **Sentinel-HealOps** project works.

---

## 1. Engine Component (`engine/`)

### 1.1 `engine/include/Order.h`
This header defines the data models for orders and trades.

```cpp
enum class Side : uint8_t { BUY, SELL };
```
- **Why `enum class`?**: It provides strong typing. You can't accidentally compare a `Side` to an integer.
- **Why `uint8_t`?**: In memory-constrained systems, using 1 byte instead of 4 (the default `int`) saves space when storing millions of orders.

```cpp
struct Order {
    uint64_t    id;
    double      price;
    uint64_t    qty;
    Side        side;
    OrderType   type;
    int64_t     timestamp_ns; 
```
- **`timestamp_ns`**: We use nanoseconds to measure the difference between order arrival and matching. In high-frequency trading, even 1 millisecond (1,000,000 ns) is considered slow.

---

### 1.2 `engine/src/OrderBook.cpp` (The Matching Engine)
This is the most critical file in the project.

#### **The Price-Time Priority Logic**
```cpp
std::map<double, PriceLevel, std::greater<double>> bids_;
std::map<double, PriceLevel>                       asks_;
```
- **Bids**: Uses `std::greater<double>` because the exchange must always match the **highest bid** first.
- **Asks**: Uses the default (lowest price first) because the exchange matches the **lowest ask** first.
- **Performance**: `std::map` is a Red-Black Tree. Searching for a price is $O(\log N)$. For millions of levels, we might use a hash map or a flat array, but for an MVP, `std::map` provides the best balance of speed and simplicity.

#### **The Matching Loop (`matchBuy`)**
```cpp
while (order.qty > 0 && !asks_.empty()) {
    auto& [ask_price, level] = *asks_.begin();
    if (order.price < ask_price) break; // Price doesn't cross
```
- **`*asks_.begin()`**: We always look at the cheapest available sell order.
- **The "If"**: If our buy price is lower than the cheapest sell price, no match is possible. The order must stay in the book as a "limit" order.

---

### 1.3 `engine/src/Logger.cpp`
This records every matching event.

```cpp
void TradeLogger::log(const Trade& t) {
    std::lock_guard lk(mtx_);
    file_ << t.matched_at_ns << ',' << t.latency_ns << ...
}
```
- **`std::lock_guard`**: This is critical. Multiple matches might happen concurrently across different order books or threads. Without locking, they would write over each other and corrupt our CSV data.

---

## 2. Project Directory & File Breakdown

### **`engine/`** (The Trading Core)
This directory contains the high-performance C++ matching engine.
- **`include/Order.h`**: The "Atom" of the system. Defines what an `Order` and a `Trade` look like. 
    - *If/But*: Uses `int64_t` for nanosecond timestamps to avoid overflow for the next ~290 years.
- **`include/OrderBook.h`**: The "Blueprint". Defines the `PriceLevel` (as a `std::deque`) and the `OrderBook` class.
- **`src/OrderBook.cpp`**: The "Brain". This contains the matching loop. 
    - [**DEEP DIVE: Line-by-Line Match Engine Walkthrough**](file:///home/iiitl/Documents/Sentinel-HealOps/docs/orderbook_walkthrough.md)
- **`src/Logger.cpp`**: The "Recorder". Writes every trade to a CSV file.

### **`brain/`** (The AI Control Plane)
A high-performance Python service that classifies anomalies.
- **`main.py`**: FastAPI app with the `/ingest` endpoint. Processes traces in real-time.
- **`model.py`**: Training script for the Random Forest model. Generates synthetic data and saves the `.pkl` artifact.
    - [**DEEP DIVE: Line-by-Line Brain & ML Walkthrough**](file:///home/iiitl/Documents/Sentinel-HealOps/docs/brain_walkthrough.md)

### **`governor/`** (The Remediation Layer)
Reacts to the Brain's decisions by executing infrastructure changes.
- **`action-webhook.py`**: A FastAPI webhook simulator that converts JSON payload actions into Kubernetes shell commands.
- **`engine-deployment.yaml`**: The Kubernetes Deployment manifest for the matching engine used during rollouts.

### **`scripts/`** (Testing & Automation)
- **`load_generator.py`**: Simulates thousands of orders per second and injects "faults" (artificial delay) so we can see the system heal.
- **`test_remediation_layer.sh`**: The end-to-end Python/Mock verification shell script.

---

## 3. Detailed Line-by-Line Code Walkthroughs

Because this project uses advanced C++ (C++20) and real-time statistics, we've created dedicated deep-dive documents:

1. **[Core Matching Logic (engine/src/OrderBook.cpp)](file:///home/iiitl/Documents/Sentinel-HealOps/docs/orderbook_walkthrough.md)**
   - Explains how Bid/Ask maps work.
   - Breakdown of the Price-Time priority loop.
   - Memory management and performance trade-offs.

2. **[Anomaly Detection Math (interceptor/src/ZScoreDetector.cpp)](file:///home/iiitl/Documents/Sentinel-HealOps/docs/detector_walkthrough.md)**
   - Explains Welford's Algorithm for online mean/variance.
   - Why simple averages fail in high-frequency monitoring.
   - The significance of the Z-Score threshold (3.0 sigma).

3. **[Brain Control Plane (brain/main.py)](file:///home/iiitl/Documents/Sentinel-HealOps/docs/brain_walkthrough.md)**
   - Explains the Random Forest generation and FastAPI integration.

4. **[Governor Webhook (governor/action-webhook.py)](file:///home/iiitl/Documents/Sentinel-HealOps/docs/governor_walkthrough.md)**
   - Explains the self-healing Kubernetes wrapper logic that automates `kubectl rollout`.

---

## 4. Operational Workflow

1. **Trade Match**: `OrderBook.cpp` finds a price-time match.
2. **Log Entry**: `Logger.cpp` writes `latency_ns` to a file.
3. **Observation**: `interceptor/main.cpp` reads the new line.
4. **Analysis**: `ZScoreDetector.cpp` flags the latency as "normal" or "outlier".
5. **Report**: An outlier triggers a raw HTTP POST to the Brain.

---

## 5. File Tailing Logic (`interceptor/src/main.cpp`)

The engine writes to a file, and the interceptor reads from it like `tail -f`.
- **Why `std::ifstream::clear()`?**: When a file hits `EOF` (End of File), C++ sets a "fail" flag. We must clear this flag so the next time the engine writes a line, we can read it.
- **Why not `inotify`?**: `inotify` is better but more complex. Tailing with a 10ms sleep is sufficient for an MVP and works on almost any version of Linux.

---

## 6. Communication Logic (The "Ifs" and "Buts")

### **Why use raw sockets for HTTP?**
In `interceptor/src/main.cpp`, we use `socket()`, `connect()`, and `send()`.
- **Pros**: Zero external libraries (no `libcurl`). Very fast.
- **Cons**: It doesn't support HTTPS (SSL/TLS). 
- **The Decision**: Since the interceptor and brain are usually on the same local network (or the same machine), raw HTTP is fine. If we move this to production, we would add MbedTLS or OpenSSL.

---

## 7. SentinelARC Integration (V2 Extension)

Sentinel-HealOps can monitor **any** latency-emitting system, not just the C++ engine.
The `scripts/sentinelarc_adapter.py` bridges the [SentinelARC](https://github.com/Ashishparmar265/SentinelARC) multi-agent system into the same pipeline.

### Data Flow
```
SentinelARC FastAPI MCP Servers (port 8001)
         │  HTTP probe (every 500ms)
         ▼
  sentinelarc_adapter.py
         │  writes → /tmp/healops_sentinel_arc.csv
         ▼
  Interceptor (io_uring tail)
         │  Z-score anomaly detection
         ▼
  Brain → TARGET_REGISTRY["sentinelarc"] → "sentinelarc-mcp"
         │  webhook
         ▼
  Governor → kubectl rollout restart deployment/sentinelarc-mcp
```

### Key Design Decisions

- **`source` field in Anomaly**: The Brain's `/ingest` endpoint now accepts a `source` string (`"engine"` or `"sentinelarc"`). This lets the `TARGET_REGISTRY` map each source to the correct Kubernetes deployment name.
- **Non-invasive**: The adapter is a standalone script. No changes needed inside the SentinelARC codebase.
- **Same Z-score math**: The adapter converts HTTP probe latency to nanoseconds and writes the same CSV column schema, so the C++ Interceptor treats SentinelARC probes identically to engine trades.

