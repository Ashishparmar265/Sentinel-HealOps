#include "OrderBook.h"
#include "Logger.h"

#include <iostream>
#include <atomic>
#include <signal.h>

static std::atomic<bool> g_running{true};

void handle_sigint(int) { g_running = false; }

int main() {
    signal(SIGINT, handle_sigint);

    const std::string log_path = "/tmp/healops_trades.csv";
    TradeLogger logger(log_path);
    std::cout << "[Engine] Logging trades to: " << log_path << '\n';

    uint64_t trade_count = 0;
    uint64_t order_id    = 1;

    auto on_trade = [&](const Trade& t) {
        logger.log(t);
        ++trade_count;
    };

    OrderBook book(on_trade);

    std::cout << "[Engine] Order Matching Engine running. Press Ctrl+C to stop.\n";
    std::cout << "[Engine] Best bid / ask will print every 5 seconds.\n";

    // Simple demo: alternately add bids and asks to generate matched trades
    auto last_report = std::chrono::steady_clock::now();
    while (g_running) {
        // Simulate two crossing orders (guaranteed match)
        book.addOrder(Order(order_id++, 100.00, 10, Side::BUY));
        book.addOrder(Order(order_id++, 100.00, 10, Side::SELL));

        auto now = std::chrono::steady_clock::now();
        if (now - last_report > std::chrono::seconds(5)) {
            std::cout << "[Engine] Trades: " << trade_count
                      << "  Bids: " << book.bidDepth()
                      << "  Asks: " << book.askDepth() << '\n';
            last_report = now;
        }
    }

    std::cout << "[Engine] Shutdown. Total trades: " << trade_count << '\n';
    return 0;
}
