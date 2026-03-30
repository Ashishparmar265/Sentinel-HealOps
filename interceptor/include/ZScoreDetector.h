#pragma once

#include "Anomaly.h"
#include <deque>
#include <cmath>
#include <functional>

// Rolling Z-score detector over a sliding window of latency samples.
// Flags a sample as anomalous if |Z| > threshold.
class ZScoreDetector {
public:
    using AnomalyCallback = std::function<void(const AnomalyEvent&)>;

    ZScoreDetector(size_t window_size, double threshold, AnomalyCallback cb)
        : window_(window_size), threshold_(threshold), on_anomaly_(std::move(cb)) {}

    // Feed a new latency_ns sample. Returns true if anomalous.
    bool feed(int64_t timestamp_ns, uint64_t buy_id, uint64_t sell_id, double latency_ns);

    double mean()   const { return mean_; }
    double stddev() const { return std::sqrt(variance_); }
    size_t count()  const { return samples_.size(); }

private:
    std::deque<double> samples_;
    size_t             window_;
    double             threshold_;
    AnomalyCallback    on_anomaly_;

    double mean_     = 0.0;
    double variance_ = 0.0;

    void updateStats(double val, bool add);
};
