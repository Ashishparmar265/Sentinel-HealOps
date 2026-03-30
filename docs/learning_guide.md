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
- **`std::lock_guard`**: This is critical. Multiple matches might happen---

## 2. Project Directory & File Breakdown

### **`engine/`** (The Trading Core)
This directory contains the high-performance C++ matching engine.
- **`include/Order.h`**: The "Atom" of the system. Defines what an `Order` and a `Trade` look like. 
    - *If/But*: Uses `int64_t` for nanosecond timestamps to avoid overflow for the next ~290 years.
- **`include/OrderBook.h`**: The "Blueprint". Defines the `PriceLevel` (as a `std::deque`) and the `OrderBook` class.
- **`src/OrderBook.cpp`**: The "Brain". This contains the matching loop. 
    - [**DEEP DIVE: Line-by-Line Match Engine Walkthrough**](file:///home/iiitl/Documents/Sentinel-HealOps/docs/orderbook_walkthrough.md)
- **`src/Logger.cpp`**: The "Recorder". Writes every trade to a CSV file.

### **`interceptor/`** (The SRE Sidecar)
A low-overhead monitor that watches the engine's performance.
- **`include/ZScoreDetector.h`**: Header for the statistical engine.
- **`src/ZScoreDetector.cpp`**: The "Math". Implements Welford's Algorithm for rolling statistics.
    - [**DEEP DIVE: Line-by-Line Math & Detector Walkthrough**](file:///home/iiitl/Documents/Sentinel-HealOps/docs/detector_walkthrough.md)
- **`src/main.cpp`**: The "Tailer". Continuously reads the trade log and sends anomalies to the Brain via raw HTTP.

### **`scripts/`** (Testing & Automation)
- **`load_generator.py`**: Simulates thousands of orders per second and injects "faults" (artificial delay) so we can see the system heal.

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

---

## 4. Operational Workflow

1. **Trade Match**: `OrderBook.cpp` finds a price-time match.
2. **Log Entry**: `Logger.cpp` writes `latency_ns` to a file.
3. **Observation**: `interceptor/main.cpp` reads the new line.
4. **Analysis**: `ZScoreDetector.cpp` flags the latency as "normal" or "outlier".
5. **Report**: An outlier triggers a raw HTTP POST to the Brain.
ts a "fail" flag. We must clear this flag so the next time the engine writes a line, we can read it.
- **Why not `inotify`?**: `inotify` is better but more complex. Tailing with a 10ms sleep is sufficient for an MVP and works on almost any version of Linux.

---

## 3. Communication Logic (The "Ifs" and "Buts")

### **Why use raw sockets for HTTP?**
In `interceptor/src/main.cpp`, we use `socket()`, `connect()`, and `send()`.
- **Pros**: Zero external libraries (no `libcurl`). Very fast.
- **Cons**: It doesn't support HTTPS (SSL/TLS). 
- **The Decision**: Since the interceptor and brain are usually on the same local network (or the same machine), raw HTTP is fine. If we move this to production, we would add MbedTLS or OpenSSL.

---

*This guide will be expanded line-by-line for Phase 2 (Python ML code).*
