#pragma once

#include "Order.h"

#include <string>
#include <fstream>
#include <mutex>

// Thread-safe file logger that writes trade execution latency records.
// Format (CSV):
//   timestamp_ns,buy_id,sell_id,price,qty,latency_ns
class TradeLogger {
public:
    explicit TradeLogger(const std::string& filepath);
    ~TradeLogger();

    void log(const Trade& t);

private:
    std::ofstream  file_;
    std::mutex     mtx_;
};
