cmake_minimum_required(VERSION 3.20)

add_library(engine_lib STATIC
    src/OrderBook.cpp
    src/Logger.cpp
)

target_include_directories(engine_lib PUBLIC include)
target_compile_options(engine_lib PRIVATE -Wall -Wextra -O2)

add_executable(matching_engine src/main.cpp)
target_link_libraries(matching_engine PRIVATE engine_lib)
