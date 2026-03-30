#pragma once

#include "Order.h"

#include <map>
#include <deque>
#include <vector>
#include <functional>
#include <mutex>
#include <shared_mutex>

// Price level: sorted queue of orders at that price
using PriceLevel = std::deque<Order>;

class OrderBook {
public:
    using TradeCallback = std::function<void(const Trade&)>;

    explicit OrderBook(TradeCallback cb) : on_trade_(std::move(cb)) {}

    // Add an order and attempt matching. Returns number of trades executed.
    int addOrder(Order order);

    // Cancel an existing order by ID. Returns true on success.
    bool cancelOrder(uint64_t order_id, Side side, double price);

    size_t bidDepth() const;
    size_t askDepth() const;

    // Best bid/ask prices (0 if empty)
    double bestBid() const;
    double bestAsk() const;

private:
    // bids: highest price first (reverse)
    std::map<double, PriceLevel, std::greater<double>> bids_;
    // asks: lowest price first (natural)
    std::map<double, PriceLevel>                       asks_;

    mutable std::shared_mutex rw_mutex_;
    TradeCallback             on_trade_;

    int matchBuy(Order& order);
    int matchSell(Order& order);
};
