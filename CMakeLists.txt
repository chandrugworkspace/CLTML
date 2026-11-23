# ==============================================================================
# CMakeLists.txt for CLTML Research Project
# Compile-Time-Bound Lookup-Table Machine Learning for Lock Selection
# Authors: Chandru G & Chethan S (PES University, CSE-AIML)
# ==============================================================================

cmake_minimum_required(VERSION 3.16)
project(CLTML C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Optimization and warning flags
add_compile_options(-O3 -march=native -Wall -Wextra -pthread)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src)

# 1. Main Hot-Path & Quiescent-Epoch Benchmark
add_executable(cltml_benchmark src/cltml_benchmark.c)
target_link_libraries(cltml_benchmark PRIVATE pthread m)

# 2. Userspace 4-Lock Benchmark Suite (Advisor Step 1-3)
add_executable(cltml_userspace_benchmark src/cltml_userspace_benchmark.c)
target_link_libraries(cltml_userspace_benchmark PRIVATE pthread m)
