#pragma once

#include <cstdint>
#include <string>

enum class Side : uint8_t { BUY, SELL };
enum class OrderType : uint8_t { LIMIT, MARKET };

struct Order {
    uint64_t    id;
    double      price;
    uint64_t    qty;
    Side        side;
    OrderType   type;
    int64_t     timestamp_ns; // epoch nanoseconds

    Order(uint64_t id, double price, uint64_t qty, Side side,
          OrderType type = OrderType::LIMIT, int64_t ts = 0)
        : id(id), price(price), qty(qty), side(side), type(type), timestamp_ns(ts) {}
};

struct Trade {
    uint64_t buy_order_id;
    uint64_t sell_order_id;
    double   price;
    uint64_t qty;
    int64_t  matched_at_ns;
    int64_t  latency_ns;  // time from order arrival to match
};
