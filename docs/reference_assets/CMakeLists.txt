cmake_minimum_required(VERSION 3.20)
project(SentinelHealOps VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Release build with -O2 by default
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_subdirectory(engine)
add_subdirectory(interceptor)

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
