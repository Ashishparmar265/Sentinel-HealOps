cmake_minimum_required(VERSION 3.20)

add_executable(interceptor
    src/main.cpp
    src/ZScoreDetector.cpp
)

target_include_directories(interceptor PRIVATE include /tmp/liburing/src/include)
target_compile_options(interceptor PRIVATE -Wall -Wextra -O2)
target_link_libraries(interceptor PRIVATE /tmp/liburing/src/liburing.a)
