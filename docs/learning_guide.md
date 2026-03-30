# Sentinel-HealOps: Project Learning Guide

Welcome to the **HealOps** learning guide. This document provides a deep dive into the architecture, code, and concepts behind the autonomous SRE system for high-frequency trading.

---

## 1. Core Concepts

### 1.1 Limit Order Book (LOB)
The heart of any exchange is the **Order Book**. It maintains a list of buy (bids) and sell (asks) orders.
- **Price-Time Priority**: Orders are matched first based on the best price. If prices are equal, the order that arrived first (time) is prioritized.
- **Data Structures**: Efficient LOBs use `std::map` or `std::set` (Red-Black Trees) for price indexing and `std::deque` or linked lists for time-priority queues at each price level.

### 1.2 Telemetry Ingestion: The "Observer Effect"
In high-frequency systems, monitoring must be as lightweight as possible. 
- **io_uring**: A Linux-native asynchronous I/O interface that minimizes context switches. It allows us to "harvest" logs directly from the kernel space without stalling the main engine threads.
- **Lock-Free Buffers**: Passing data between the engine and the sidecar using ring buffers ensures the "Matching Path" is never blocked by "Logging Path".

### 1.3 Statistical Anomaly Detection (Z-Score)
Before using heavy AI models, we use simple math to filter the noise.
- **Z-Score Formula**: $Z = \frac{x - \mu}{\sigma}$
- **Dynamic Thresholding**: We calculate a rolling mean ($\mu$) and standard deviation ($\sigma$) of trade latencies. If a new trade's latency ($x$) has a Z-score $> 3$, it's an outlier (anomaly).

---

## 2. Code Walkthrough

### 2.1 The Engine (`/engine`)
- **`Order.h`**: Defines the `Order` and `Trade` structures. We use `timestamp_ns` (nanoseconds) to measure sub-millisecond performance.
- **`OrderBook.cpp`**: Implements the matching logic. 
    - `matchBuy()`: Iterates through the `asks_` map (lowest price first).
    - `matchSell()`: Iterates through the `bids_` map (highest price first).
- **`Logger.cpp`**: A thread-safe CSV writer. In a production system, this would be replaced by a memory-mapped file or a ring buffer.

### 2.2 The Interceptor (`/interceptor`)
- **`ZScoreDetector.cpp`**: Uses **Welford’s Algorithm** for "online" calculation of mean and variance. This is mathematically more stable than traditional methods when dealing with thousands of samples per second.
- **`main.cpp`**: Acts as a "tail -f" for the trade log. It feeds every line into the detector and triggers an HTTP POST if an anomaly is found.

### 2.3 The Brain (`/brain`)
- **FastAPI**: A high-performance Python framework.
- **Random Forest**: Why RF? It's fast at inference time and handles non-linear relationships well (e.g., "CPU spike + Memory leak" = `CRITICAL_FAILURE`).

---

## 3. Workflow Summary

1. **Order Input**: User sends a BUY/SELL limit order.
2. **Matching**: Engine matches it against the book.
3. **Trace**: Match details (latency) are logged to `/tmp/healops_trades.csv`.
4. **Ingestion**: Interceptor sidecar reads the CSV in real-time.
5. **Detection**: Interceptor calculates Z-score. If $Z > 3$, it flags an anomaly.
6. **Classification**: Brain (Python) receives the flag and classifies it (e.g., "Network Degradation").
7. **Remediation**: Governor triggers a GitHub Actions rollback to a stable container image.

---

## 4. How to Build & Learn

### Prerequisites
- Linux (Ubuntu/Mint)
- C++20 Compiler (GCC/Clang)
- CMake 3.20+
- Python 3.11+

### Build Steps
```bash
# 1. Compile the C++ components
mkdir build && cd build
cmake ..
make -j$(nproc)

# 2. Run the Engine
./engine/matching_engine

# 3. Run the Interceptor (in a new tab)
./interceptor/interceptor
```

---

## 5. Regular Updates
This document will be updated as we implement **Phase 2 (AI Training)** and **Phase 3 (Auto-Remediation)**.

> [!TIP]
> Focus on the `latency_ns` logic in `OrderBook.cpp` — it is the primary metric that HealOps monitors.
