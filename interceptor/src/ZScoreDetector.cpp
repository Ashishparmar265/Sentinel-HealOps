#include "ZScoreDetector.h"

bool ZScoreDetector::feed(int64_t timestamp_ns, uint64_t buy_id, uint64_t sell_id, double latency_ns) {
    // Add new sample
    updateStats(latency_ns, true);
    samples_.push_back(latency_ns);

    // Evict oldest if window exceeded
    if (samples_.size() > window_) {
        double oldest = samples_.front();
        samples_.pop_front();
        updateStats(oldest, false);
    }

    // Wait until we have enough samples for a stable estimate
    if (samples_.size() < 30) return false;

    double sigma = stddev();
    if (sigma < 1e-9) return false; // avoid div/0

    double z = (latency_ns - mean_) / sigma;
    if (std::abs(z) > threshold_) {
        AnomalyEvent evt;
        evt.timestamp_ns   = timestamp_ns;
        evt.buy_order_id   = buy_id;
        evt.sell_order_id  = sell_id;
        evt.latency_ms     = latency_ns / 1e6;
        evt.z_score        = z;
        evt.fault_type     = "LATENCY_SPIKE";
        on_anomaly_(evt);
        return true;
    }
    return false;
}

// Welford's online algorithm for incremental mean/variance
void ZScoreDetector::updateStats(double val, bool add) {
    if (add) {
        size_t n  = samples_.size() + 1;
        double delta  = val - mean_;
        mean_        += delta / n;
        double delta2 = val - mean_;
        variance_    += (delta * delta2 - variance_) / n;
    } else {
        size_t n = samples_.size();
        if (n <= 1) { mean_ = 0.0; variance_ = 0.0; return; }
        double delta  = val - mean_;
        mean_        -= delta / (n - 1);
        double delta2 = val - mean_;
        variance_    -= (delta * delta2 + variance_) / (n - 1);
        if (variance_ < 0.0) variance_ = 0.0;
    }
}
