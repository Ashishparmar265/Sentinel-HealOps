# Exhaustive Walkthrough: `interceptor/src/ZScoreDetector.cpp`

This document explains the math and logic behind the anomaly detection system.

---

## 1. Welford's Algorithm (The Online Statistician)

```cpp
void ZScoreDetector::updateStats(double val, bool add) {
    if (add) {
        size_t n = samples_.size() + 1; // [1]
        double delta = val - mean_; // [2]
        mean_ += delta / n; // [3]
```
- **[1] `n`**: The new sample size.
- **[2] `delta`**: The difference between the new value and the current average.
- **[3] `mean_ += delta / n`**: This is the **Incremental Mean**. Instead of summing all numbers and dividing, we slightly adjust the current mean by a fraction of the new data.

```cpp
        double delta2 = val - mean_; // [4]
        variance_ += (delta * delta2 - variance_) / n; // [5]
```
- **[4] `delta2`**: The difference after the mean has been updated.
- **[5] `variance_`**: This is an online update for **M2** (Sum of Squares of Differences). It allows us to track standard deviation without re-calculating everything.

---

## 2. `ZScoreDetector::feed`
This function is called for every trade logged by the engine.

```cpp
if (samples_.size() > window_) { // [6]
    double oldest = samples_.front();
    samples_.pop_front();
    updateStats(oldest, false); // [7]
}
```
- **[6] Rolling Window**: We only care about recent data (e.g., the last 1000 trades).
- **[7] `updateStats(..., false)`**: This **removes** the effect of the oldest trade from our mean and variance calculations. This makes the detector "forget" the past and adapt to the present.

```cpp
if (samples_.size() < 30) return false; // [8]
```
- **[8] Warm-up**: Statistics are unreliable with very few samples (e.g., 2 or 3 trades). We wait for 30 trades to get a "stable" baseline before we start flagging anomalies.

```cpp
double z = (latency_ns - mean_) / sigma; // [9]
```
- **[9] Z-Score**: It measures "Standard Deviations". 
    - Z = 0: Perfectly average.
    - Z = 1: Slightly slow.
    - Z = 3: **Extremely rare (Anomaly)**. In a normal distribution, 99.7% of data is within $Z \le 3$.

---

## 3. The "Ifs" and "Buts" of the Math

- **"But" what if latency is 0?**
    - If `sigma` (Standard Deviation) is 0 (all latencies are identical), the code hits line 24: `if (sigma < 1e-9) return false;`. This prevents "Division by Zero" crashes.
- **"If" the system gets faster?**
    - If the engine gets faster, the `mean_` will decrease over time. A Z-score can be **negative** (meaning the trade was faster than average). Our code uses `std::abs(z)` to detect both extreme slowness AND extreme speed (which can also indicate a bug).
- **"Why" Welford's over simple loops?**
    - A simple loop `for(val : samples) { sum += val; }` is $O(N)$ every time a trade happens. 
    - Welford's is $O(1)$. It's much faster and can handle millions of trades without LAG.

---

*Phase 2 will add the line-by-line guide for the Python Random Forest model.*
