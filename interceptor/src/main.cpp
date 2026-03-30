#include "ZScoreDetector.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <chrono>
#include <thread>
#include <atomic>
#include <signal.h>
#include <cstring>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>

static std::atomic<bool> g_running{true};

void handle_sigint(int) { g_running = false; }

// --------------------------------------------------------------------------
// Minimal HTTP POST sender (no dependencies)
// --------------------------------------------------------------------------
static bool httpPost(const std::string& host, int port,
                     const std::string& path, const std::string& body) {
    int sock = ::socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return false;

    struct timeval tv{ .tv_sec = 1, .tv_usec = 0 };
    ::setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port);
    ::inet_pton(AF_INET, host.c_str(), &addr.sin_addr);

    if (::connect(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        ::close(sock);
        return false;
    }

    std::string req =
        "POST " + path + " HTTP/1.0\r\n"
        "Host: " + host + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + std::to_string(body.size()) + "\r\n"
        "Connection: close\r\n\r\n" + body;

    ::send(sock, req.c_str(), req.size(), 0);
    ::close(sock);
    return true;
}

// --------------------------------------------------------------------------
// CSV tail reader — follows the log file as new rows appear
// --------------------------------------------------------------------------
int main(int argc, char* argv[]) {
    signal(SIGINT, handle_sigint);

    const std::string log_path   = (argc > 1) ? argv[1] : "/tmp/healops_trades.csv";
    const std::string brain_host = (argc > 2) ? argv[2] : "127.0.0.1";
    const int         brain_port = (argc > 3) ? std::stoi(argv[3]) : 8000;
    const double      z_thresh   = 3.0;
    const size_t      window     = 1000;

    auto on_anomaly = [&](const AnomalyEvent& evt) {
        std::cout << "[Interceptor] ⚡ ANOMALY | latency="
                  << evt.latency_ms << "ms | Z=" << evt.z_score
                  << " | " << evt.fault_type << '\n';

        // Build JSON payload
        std::ostringstream json;
        json << "{"
             << "\"timestamp_ns\":"  << evt.timestamp_ns  << ","
             << "\"buy_id\":"        << evt.buy_order_id  << ","
             << "\"sell_id\":"       << evt.sell_order_id << ","
             << "\"latency_ms\":"    << evt.latency_ms    << ","
             << "\"z_score\":"       << evt.z_score       << ","
             << "\"fault_type\":\""  << evt.fault_type    << "\""
             << "}";

        bool ok = httpPost(brain_host, brain_port, "/ingest", json.str());
        if (!ok)
            std::cerr << "[Interceptor] Warning: could not reach Brain at "
                      << brain_host << ':' << brain_port << '\n';
    };

    ZScoreDetector detector(window, z_thresh, on_anomaly);

    std::ifstream file(log_path);
    if (!file.is_open()) {
        // Wait for the file to appear (engine may not have started yet)
        std::cout << "[Interceptor] Waiting for log file: " << log_path << '\n';
        while (!file.is_open() && g_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            file.open(log_path);
        }
    }

    std::cout << "[Interceptor] Tailing: " << log_path << '\n';
    std::cout << "[Interceptor] Brain endpoint: " << brain_host << ':' << brain_port << '\n';
    std::cout << "[Interceptor] Z-threshold: " << z_thresh
              << "  Window: " << window << '\n';

    std::string line;
    std::getline(file, line); // skip CSV header

    uint64_t processed = 0;
    uint64_t anomalies = 0;
    auto last_report   = std::chrono::steady_clock::now();

    while (g_running) {
        if (std::getline(file, line) && !line.empty()) {
            std::istringstream ss(line);
            std::string tok;
            std::vector<std::string> cols;
            while (std::getline(ss, tok, ','))
                cols.push_back(tok);

            if (cols.size() < 6) continue;

            int64_t  ts         = std::stoll(cols[0]);
            uint64_t buy_id     = std::stoull(cols[1]);
            uint64_t sell_id    = std::stoull(cols[2]);
            double   latency_ns = std::stod(cols[5]);

            bool flagged = detector.feed(ts, buy_id, sell_id, latency_ns);
            ++processed;
            if (flagged) ++anomalies;

            auto now = std::chrono::steady_clock::now();
            if (now - last_report > std::chrono::seconds(5)) {
                std::cout << "[Interceptor] Processed=" << processed
                          << "  Anomalies=" << anomalies
                          << "  μ=" << detector.mean() / 1e6 << "ms"
                          << "  σ=" << detector.stddev() / 1e6 << "ms\n";
                last_report = now;
            }
        } else {
            // EOF — wait for more data
            file.clear();
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }

    std::cout << "[Interceptor] Shutdown. Processed=" << processed
              << "  Anomalies=" << anomalies << '\n';
    return 0;
}
