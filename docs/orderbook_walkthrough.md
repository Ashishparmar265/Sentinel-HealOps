# Exhaustive Walkthrough: `engine/src/OrderBook.cpp`

This document explains every single line of the matching engine's core logic.

---

## 1. `OrderBook::addOrder`
This function is the entry point for every new order.

```cpp
int OrderBook::addOrder(Order order) {
    std::unique_lock lock(rw_mutex_); // [1]
```
- **[1] `std::unique_lock`**: We use a "Write Lock" here. If multiple people are trading, we must ensure only one person modifies the book at a time to prevent data corruption.
- **If/But**: Why not `shared_lock`? A `shared_lock` allows many readers but NO writers. Since we are *adding* an order (writing), we need `unique_lock`.

```cpp
    if (order.timestamp_ns == 0)
        order.timestamp_ns = now_ns(); // [2]
```
- **[2] `now_ns()`**: If the order doesn't have a time (e.g., from a test script), we stamp it here. This "Arrival Time" is used later to calculate latency.

---

## 2. `OrderBook::matchBuy`
This is how we find sellers for a buyer.

```cpp
while (order.qty > 0 && !asks_.empty()) { // [3]
```
- **[3] The Loop**: We keep matching as long as the buyer still wants more (`qty > 0`) and there are sellers (`asks_`) available.

```cpp
    auto& [ask_price, level] = *asks_.begin(); // [4]
```
- **[4] `asks_.begin()`**: This is the "Best Ask" (lowest price). Since the buyer wants the cheapest price, we always start here.

```cpp
    if (order.price < ask_price) break; // [5]
```
- **[5] The Price Check**: If the buyer is offering $100 but the cheapest seller wants $101, no match is possible. We `break` the loop.

```cpp
    while (order.qty > 0 && !level.empty()) { // [6]
```
- **[6] Inner Loop**: One price level might have many orders. We match them one by one (Time Priority).

```cpp
        Order& resting = level.front(); // [7]
        uint64_t fill = std::min(order.qty, resting.qty); // [8]
```
- **[7] `level.front()`**: The oldest order at this price (Time Priority).
- **[8] `std::min`**: We match as much as possible. If the buyer wants 100 but the seller only has 20, we match 20.

```cpp
        Trade t;
        t.buy_order_id = order.id;
        t.latency_ns = now_ns() - order.timestamp_ns; // [9]
```
- **[9] Latency Calculation**: This is the heart of HealOps. We subtract the arrival time from the match time. If this number is high, the sidecar detects an anomaly.

```cpp
        order.qty -= fill;
        resting.qty -= fill; // [10]
```
- **[10] Updating State**: We subtract the matched amount from both orders.

```cpp
        if (resting.qty == 0) level.pop_front(); // [11]
```
- **[11] Cleanup**: If the seller's order is fully filled, we remove it from the book.

---

## 3. The "Ifs" and "Buts" of this Logic

- **What if the book is empty?**
    - The `while (!asks_.empty())` handles this. If there's no one to match with, the code skips the loop and adds the order to the `bids_` map (resting order).
- **What if price is 0?**
    - The code doesn't explicitly check for 0, but since we match `order.price >= ask_price`, a 0 bid will never match unless there's a 0 or negative ask (rare in finance).
- **Why `std::deque`?**
    - `std::deque` is faster than `std::vector` for removing items from the front (`pop_front`). Since we strictly match the oldest orders first, `pop_front` is a constant $O(1)$ operation.

---

*This line-by-line guide will be updated for the Interceptor next.*
