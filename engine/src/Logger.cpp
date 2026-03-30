#include "Logger.h"

#include <iomanip>
#include <sstream>

TradeLogger::TradeLogger(const std::string& filepath)
    : file_(filepath, std::ios::app)
{
    if (!file_.is_open())
        throw std::runtime_error("Cannot open log file: " + filepath);

    // Write CSV header if empty
    file_.seekp(0, std::ios::end);
    if (file_.tellp() == 0)
        file_ << "timestamp_ns,buy_id,sell_id,price,qty,latency_ns\n";
}

TradeLogger::~TradeLogger() {
    if (file_.is_open()) file_.flush();
}

void TradeLogger::log(const Trade& t) {
    std::lock_guard lk(mtx_);
    file_ << t.matched_at_ns   << ','
          << t.buy_order_id    << ','
          << t.sell_order_id   << ','
          << std::fixed << std::setprecision(2) << t.price << ','
          << t.qty             << ','
          << t.latency_ns      << '\n';
}
