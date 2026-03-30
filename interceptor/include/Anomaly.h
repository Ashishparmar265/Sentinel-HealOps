#pragma once
#include <cstdint>
#include <string>

struct AnomalyEvent {
    int64_t  timestamp_ns;
    uint64_t buy_order_id;
    uint64_t sell_order_id;
    double   latency_ms;
    double   z_score;
    std::string fault_type; // e.g. "LATENCY_SPIKE"
};
