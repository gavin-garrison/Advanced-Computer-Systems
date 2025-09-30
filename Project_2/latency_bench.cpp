// src/latency_bench.cpp
#include "util.h"
#include <vector>
#include <random>
#include <algorithm>
#include <numeric>
#include <cstdlib>

enum class Pattern { SEQ, STRIDE, RANDOM };

static void build_ring(uint64_t* idx, size_t N, Pattern pat, size_t stride_elems) {
  std::vector<size_t> order(N);
  if (pat == Pattern::RANDOM) {
    std::iota(order.begin(), order.end(), 0);
    std::mt19937_64 rng(42);
    std::shuffle(order.begin(), order.end(), rng);
  } else if (pat == Pattern::STRIDE) {
    for (size_t i = 0, p = 0; i < N; ++i, p = (p + stride_elems) % N) order[i] = p;
  } else {
    std::iota(order.begin(), order.end(), 0);
  }
  for (size_t i = 0; i < N; ++i) {
    size_t nxt = order[(i+1) % N];
    idx[ order[i] ] = nxt;
  }
}

static double chase_ns(uint64_t* idx, size_t N, size_t iters) {
  volatile uint64_t p = 0;
  uint64_t t0 = rdtsc_now();
  for (size_t i = 0; i < iters; ++i) p = idx[p];
  uint64_t t1 = rdtscp_now();
  double cycles = double(t1 - t0) / double(iters);
  // If you want exact Hz, pass CPU_HZ env (e.g., setx CPU_HZ 4200000000)
  const char* f = std::getenv("CPU_HZ");
  double hz = f ? std::atof(f) : 3.5e9; // fallback estimate
  return (cycles / hz) * 1e9;
}

static void do_latency_size_sweep(size_t min_kb, size_t max_mb, Pattern pat, size_t strideB,
                                  size_t iters, int cpu, int reps) {
  pin_to_cpu(cpu);
  CSV csv;
  csv.set_header("bytes,pattern,stride_B,iter,repetition,lat_ns_est");
  for (size_t sz = min_kb*1024ULL; sz <= max_mb*1024ULL*1024ULL; sz <<= 1) {
    size_t N = std::max<size_t>(4, sz / sizeof(uint64_t));
    std::vector<uint64_t> buf(N);
    size_t stride_elems = std::max<size_t>(1, strideB / sizeof(uint64_t));
    build_ring(buf.data(), N, pat, stride_elems);
    touch_memory(buf.data(), sz); // prefault
    for (int r=0; r<reps; ++r) {
      double ns = chase_ns(buf.data(), N, iters);
      csv.add_row(std::to_string(sz) + "," +
                  (pat==Pattern::RANDOM?"random":pat==Pattern::STRIDE?"stride":"seq") + "," +
                  std::to_string(strideB) + "," +
                  std::to_string(iters) + "," +
                  std::to_string(r) + "," +
                  std::to_string(ns));
    }
  }
  csv.print();
}

void run_latency_bench(int argc, char** argv) {
  size_t min_kb = 8, max_mb = 1024; // 8KB→1GB
  size_t strideB = 64;
  size_t iters = 10'000'000;
  int cpu = -1, reps = 3;
  Pattern pat = Pattern::RANDOM;

  for (int i=1; i<argc; ) {
    if (parse_szt(i,argc,argv,"--min_kb", min_kb)) {}
    else if (parse_szt(i,argc,argv,"--max_mb", max_mb)) {}
    else if (parse_szt(i,argc,argv,"--stride", strideB)) {}
    else if (parse_szt(i,argc,argv,"--iters", iters)) {}
    else if (parse_int(i,argc,argv,"--cpu", cpu)) {}
    else if (parse_int(i,argc,argv,"--reps", reps)) {}
    else if (parse_flag(i,argc,argv,"--pattern=seq")) pat = Pattern::SEQ;
    else if (parse_flag(i,argc,argv,"--pattern=stride")) pat = Pattern::STRIDE;
    else if (parse_flag(i,argc,argv,"--pattern=random")) pat = Pattern::RANDOM;
    else ++i;
  }

  do_latency_size_sweep(min_kb, max_mb, pat, strideB, iters, cpu, reps);
}
