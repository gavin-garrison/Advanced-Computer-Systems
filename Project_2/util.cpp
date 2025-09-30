//
// Created by Gavin Garrison on 9/14/2025.
//#include "util.h"
#include "util.h"
#include <algorithm>
#include <cstring>
#include <cmath>
#include <string>   // for stoi/stoul/stod/stoull
#include <cstdint>  // for uint8_t/uint64_t

#ifdef _WIN32
  #ifndef NOMINMAX
  #define NOMINMAX
  #endif
  #include <windows.h>
  #include <intrin.h>
#else
  #include <sched.h>
  #include <pthread.h>
  #include <unistd.h>
  #include <sys/mman.h>
#endif
// ------- parsing -------
static bool next_has(int i, int argc) { return (i+1) < argc; }

bool parse_flag(int& i, int argc, char** argv, const char* flag) {
    if (i < argc && std::strcmp(argv[i], flag) == 0) { ++i; return true; }
    return false;
}
bool parse_int (int& i, int argc, char** argv, const char* flag, int& out) {
    if (i < argc && std::strcmp(argv[i], flag)==0 && next_has(i,argc)) { out = std::stoi(argv[++i]); ++i; return true; }
    return false;
}
bool parse_szt (int& i, int argc, char** argv, const char* flag, size_t& out) {
    if (i < argc && std::strcmp(argv[i], flag)==0 && next_has(i,argc)) { out = (size_t)std::stoull(argv[++i]); ++i; return true; }
    return false;
}
bool parse_dbl (int& i, int argc, char** argv, const char* flag, double& out) {
    if (i < argc && std::strcmp(argv[i], flag)==0 && next_has(i,argc)) { out = std::stod(argv[++i]); ++i; return true; }
    return false;
}
bool parse_uint(int& i, int argc, char** argv, const char* flag, unsigned& out) {
    if (i < argc && std::strcmp(argv[i], flag)==0 && next_has(i,argc)) { out = (unsigned)std::stoul(argv[++i]); ++i; return true; }
    return false;
}

// ------- pinning -------
void pin_to_cpu(int cpu) {
    if (cpu < 0) return;
#ifdef _WIN32
    DWORD_PTR mask = (1ull << (cpu & 63));
    SetThreadAffinityMask(GetCurrentThread(), mask);
#else
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
#endif
}

// ------- memory touch / hugepages -------
void prefault_bytes(uint8_t* p, size_t n, size_t page) {
    if (!p || n==0) return;
    for (size_t i=0; i<n; i+=page) p[i] = uint8_t(i);
}

void prefer_hugepages(void* ptr, size_t n) {
#ifdef __linux__
    if (!ptr || n==0) return;
    madvise(ptr, n, MADV_HUGEPAGE);
#else
    (void)ptr; (void)n; // no-op on Windows
#endif
}

// ------- stats -------
Stats mean_stdev(const std::vector<double>& v) {
    Stats s{};
    if (v.empty()) return s;
    double m=0.0; for (double x: v) m+=x; m/=double(v.size());
    double var=0.0; for (double x: v) { double d=x-m; var += d*d; }
    var /= (v.size()>1? (v.size()-1) : 1);
    s.mean = m; s.stdev = std::sqrt(var);
    return s;
}

// ------- cycle counters -------
uint64_t rdtsc_now() {
#ifdef _WIN32
    return __rdtsc();
#else
    unsigned lo, hi;
    asm volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return (uint64_t(hi) << 32) | lo;
#endif
}

uint64_t rdtscp_now() {
#ifdef _WIN32
    unsigned int aux;
    return __rdtscp(&aux);
#else
    unsigned lo, hi;
    asm volatile ("rdtscp" : "=a"(lo), "=d"(hi) :: "%rcx");
    return (uint64_t(hi) << 32) | lo;
#endif
}
