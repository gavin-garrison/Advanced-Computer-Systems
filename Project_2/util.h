#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include <chrono>
#include <cstdio>

// ---------- tiny CSV helper ----------
struct CSV {
    std::string header;
    std::vector<std::string> rows;
    void set_header(const std::string& h) { header = h; }
    void add_row(const std::string& r) { rows.push_back(r); }
    void print() const {
        if (!header.empty()) std::puts(header.c_str());
        for (auto& r : rows) std::puts(r.c_str());
    }
};

// ---------- timing ----------
using clk = std::chrono::high_resolution_clock;
using ns  = std::chrono::nanoseconds;
struct Timer {
    clk::time_point t0{};
    void start() { t0 = clk::now(); }
    double stop_s() {
        ns dt = std::chrono::duration_cast<ns>(clk::now() - t0);
        return double(dt.count()) * 1e-9;
    }
};

// ---------- parsing helpers (replace getopt) ----------
bool parse_flag(int& i, int argc, char** argv, const char* flag);
bool parse_int (int& i, int argc, char** argv, const char* flag, int& out);
bool parse_szt (int& i, int argc, char** argv, const char* flag, size_t& out); // NOTE: size_t&
bool parse_dbl (int& i, int argc, char** argv, const char* flag, double& out);
bool parse_uint(int& i, int argc, char** argv, const char* flag, unsigned& out);

// ---------- system & memory ----------
void pin_to_cpu(int cpu);                             // -1 = no pin
void prefault_bytes(uint8_t* p, size_t n, size_t page = 4096);
inline void touch_memory(void* p, size_t n) { prefault_bytes(reinterpret_cast<uint8_t*>(p), n); }
void prefer_hugepages(void* ptr, size_t n);           // no-op on Windows; MADV_HUGEPAGE on Linux

// ---------- stats ----------
struct Stats { double mean=0.0, stdev=0.0; };
Stats mean_stdev(const std::vector<double>& v);

// ---------- cycle counters (used by latency bench) ----------
uint64_t rdtsc_now();
uint64_t rdtscp_now();
