cmake_minimum_required(VERSION 3.20)

add_executable(interceptor
    src/main.cpp
    src/ZScoreDetector.cpp
)

target_include_directories(interceptor PRIVATE include)
target_compile_options(interceptor PRIVATE -Wall -Wextra -O2)
