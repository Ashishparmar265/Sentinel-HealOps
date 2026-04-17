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

## 2. Kernel File Tailing (`io_uring`)

The Interceptor utilizes Linux's Native `io_uring` to perform zero-copy file monitoring on the CSV trade traces, circumventing `std::ifstream` blocking overhead.

```cpp
    struct io_uring ring;
    io_uring_queue_init(64, &ring, 0); // [4]
```
- **[4] Submission Queue Integration**: Here we initialize an asynchronous polling ring with 64 slots for continuous kernel reads. 

```cpp
    while (g_running) { // [5]
        struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
        io_uring_prep_read(sqe, fd, buffer, sizeof(buffer), offset); // [6]
        io_uring_submit(&ring);

        struct io_uring_cqe *cqe;
        io_uring_wait_cqe(&ring, &cqe); // [7]
```
- **[5] `g_running`**: A global atomic bool tracking SIGINT bounds.
- **[6] Submission Queue Entry (`SQE`)**: We ask the Kernel directly to populate `buffer[4096]` asynchronously starting at the `offset`. This avoids standard userspace buffering paths.
- **[7] Completion Queue Entry (`CQE`)**: We block shortly and poll the CQE array till the OS yields our telemetry packet. By only checking `cqe->res`, we identify whether we've reached EOF without triggering global error flags like standard loops natively do!

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
