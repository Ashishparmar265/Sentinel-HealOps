# Exhaustive Walkthrough: `interceptor/src/main.cpp`

This document explains the I/O operations and operational flow of the C++ Interceptor. The Interceptor sits between the Matching Engine and the Python Control Plane, acting as an anomaly-detector sidecar.

---

## 1. Minimal HTTP POST Logic (Zero Dependencies)

The interceptor needs to send JSON to the Brain without external libraries (like `libcurl`).

```cpp
static bool httpPost(const std::string& host, int port,
                     const std::string& path, const std::string& body) {
    int sock = ::socket(AF_INET, SOCK_STREAM, 0); // [1]
```
- **[1] `::socket`**: Creates a raw TCP socket. By doing this manually, we keep the binary extremely small and statically compiled.

```cpp
    struct timeval tv{ .tv_sec = 1, .tv_usec = 0 };
    ::setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)); // [2]
```
- **[2] `SO_RCVTIMEO`**: Sets a timeout. If the Python Brain crashes, we don't want the C++ interceptor hanging forever waiting for an HTTP response. We timeout after 1 second.

```cpp
    std::string req =
        "POST " + path + " HTTP/1.0\r\n"
        "Host: " + host + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + std::to_string(body.size()) + "\r\n"
        "Connection: close\r\n\r\n" + body; // [3]
```
- **[3] HTTP Payload Generation**: We manually construct the HTTP `/1.0` headers. Note the `\r\n\r\n` which signals the end of the headers and the start of the JSON `body`.

---

## 2. File Tailing Logic (The `while` loop)

The Interceptor acts like `tail -f` on the engine's CSV trade trace.

```cpp
    std::ifstream file(log_path);
    if (!file.is_open()) {
        // ... Wait for file
        while (!file.is_open() && g_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500)); // [4]
            file.open(log_path);
        }
    }
```
- **[4] Wait Loop**: Start sequences matter. If we spin up the `interceptor` before the `engine` creates `/tmp/healops_trades.csv`, the interceptor shouldn't crash. It patiently polls for the file.

```cpp
    while (g_running) { // [5]
        if (std::getline(file, line) && !line.empty()) { // [6]
            // ... Parse and feed to Z-Score ...
        } else {
            file.clear(); // [7]
            std::this_thread::sleep_for(std::chrono::milliseconds(10)); // [8]
        }
    }
```
- **[5] `g_running`**: A global atomic bool. If you send `SIGINT` (Ctrl+C), it turns false and shuts down cleanly.
- **[6] `std::getline`**: We try to read a line. If the line exists, we parse it and feed it to the Z-score detector.
- **[7] `file.clear()`**: When we reach the End Of File (EOF), the stream enters a `fail` state. We must `clear()` this flag so we can attempt to read again on the next loop iteration.
- **[8] The Sleep**: If there were no trades, we sleep for 10ms to avoid pegging the CPU at 100%.

---

## 3. Connecting to the Detector

```cpp
    auto on_anomaly = [&](const AnomalyEvent& evt) { // [9]
        // ... construct JSON ...
        httpPost(brain_host, brain_port, "/ingest", json.str());
    };
    
    ZScoreDetector detector(window, z_thresh, on_anomaly); // [10]
```
- **[9] The Lambda Callback**: We define an inline function `on_anomaly`. This captures our host and port settings.
- **[10] The Detector Initialization**: We pass the lambda to `ZScoreDetector`. Whenever the detector flags a latency spike, it immediately executes `on_anomaly`, triggering our lightweight `httpPost` to the Brain.

---

*This guide ensures the telemetry layer's logic is fully transparent for review.*
