#include "OrderBook.h"

#include <chrono>
#include <stdexcept>

static int64_t now_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

int OrderBook::addOrder(Order order) {
    std::unique_lock lock(rw_mutex_);

    if (order.timestamp_ns == 0)
        order.timestamp_ns = now_ns();

    if (order.side == Side::BUY)
        return matchBuy(order);
    else
        return matchSell(order);
}

bool OrderBook::cancelOrder(uint64_t order_id, Side side, double price) {
    std::unique_lock lock(rw_mutex_);

    if (side == Side::BUY) {
        auto it = bids_.find(price);
        if (it == bids_.end()) return false;
        auto& level = it->second;
        for (auto qit = level.begin(); qit != level.end(); ++qit) {
            if (qit->id == order_id) {
                level.erase(qit);
                if (level.empty()) bids_.erase(it);
                return true;
            }
        }
    } else {
        auto it = asks_.find(price);
        if (it == asks_.end()) return false;
        auto& level = it->second;
        for (auto qit = level.begin(); qit != level.end(); ++qit) {
            if (qit->id == order_id) {
                level.erase(qit);
                if (level.empty()) asks_.erase(it);
                return true;
            }
        }
    }
    return false;
}

size_t OrderBook::bidDepth() const {
    std::shared_lock lock(rw_mutex_);
    return bids_.size();
}

size_t OrderBook::askDepth() const {
    std::shared_lock lock(rw_mutex_);
    return asks_.size();
}

double OrderBook::bestBid() const {
    std::shared_lock lock(rw_mutex_);
    return bids_.empty() ? 0.0 : bids_.begin()->first;
}

double OrderBook::bestAsk() const {
    std::shared_lock lock(rw_mutex_);
    return asks_.empty() ? 0.0 : asks_.begin()->first;
}

// ─── Private ────────────────────────────────────────────────────────────────

int OrderBook::matchBuy(Order& order) {
    int trades = 0;
    int64_t arrival = order.timestamp_ns;

    // Walk ask price levels from lowest upward
    while (order.qty > 0 && !asks_.empty()) {
        auto& [ask_price, level] = *asks_.begin();

        bool crossable = (order.type == OrderType::MARKET)
                       || (order.price >= ask_price);
        if (!crossable) break;

        while (order.qty > 0 && !level.empty()) {
            Order& resting = level.front();
            uint64_t fill  = std::min(order.qty, resting.qty);

            Trade t;
            t.buy_order_id  = order.id;
            t.sell_order_id = resting.id;
            t.price         = ask_price;
            t.qty           = fill;
            t.matched_at_ns = now_ns();
            t.latency_ns    = t.matched_at_ns - arrival;

            order.qty   -= fill;
            resting.qty -= fill;

            on_trade_(t);
            trades++;

            if (resting.qty == 0)
                level.pop_front();
        }

        if (level.empty())
            asks_.erase(asks_.begin());
    }

    // Remaining qty → resting bid
    if (order.qty > 0 && order.type == OrderType::LIMIT)
        bids_[order.price].push_back(order);

    return trades;
}

int OrderBook::matchSell(Order& order) {
    int trades = 0;
    int64_t arrival = order.timestamp_ns;

    while (order.qty > 0 && !bids_.empty()) {
        auto& [bid_price, level] = *bids_.begin();

        bool crossable = (order.type == OrderType::MARKET)
                       || (order.price <= bid_price);
        if (!crossable) break;

        while (order.qty > 0 && !level.empty()) {
            Order& resting = level.front();
            uint64_t fill  = std::min(order.qty, resting.qty);

            Trade t;
            t.buy_order_id  = resting.id;
            t.sell_order_id = order.id;
            t.price         = bid_price;
            t.qty           = fill;
            t.matched_at_ns = now_ns();
            t.latency_ns    = t.matched_at_ns - arrival;

            order.qty   -= fill;
            resting.qty -= fill;

            on_trade_(t);
            trades++;

            if (resting.qty == 0)
                level.pop_front();
        }

        if (level.empty())
            bids_.erase(bids_.begin());
    }

    if (order.qty > 0 && order.type == OrderType::LIMIT)
        asks_[order.price].push_back(order);

    return trades;
}
