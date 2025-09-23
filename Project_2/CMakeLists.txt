cmake_minimum_required(VERSION 3.20)
project(memlab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if (MSVC)
    add_compile_options(/O2 /DNOMINMAX)
else()
    add_compile_options(-O3 -march=native)
endif()

add_executable(memlab
        main.cpp
        util.cpp
        latency_bench.cpp
        bandwidth_bench.cpp
        kernel_bench.cpp
)

if (WIN32)
    target_link_libraries(memlab PRIVATE ws2_32)
endif()
