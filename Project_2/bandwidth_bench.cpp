// src/bandwidth_bench.cpp
#include "util.h"
#include <vector>
#include <thread>
#include <atomic>
#include <cstring>
#include <string>
#include <cstdint>

enum class RW  { R, W, R70W30, R50W50 };
enum class Pat { SEQ, RANDOM };

struct Work {
  uint8_t* base;
  size_t   bytes;
  size_t   stride;
  RW       rw;
  size_t   iters;
  Pat      pat;
  uint64_t seed;
  double   gbps_out;
};

// Approx memory-interface traffic per touch (bytes)
static inline double effective_bytes_per_touch(RW rw) {
  switch (rw) {
    case RW::R:        return 64.0;                          // one cache line read
    case RW::W:        return 128.0;                         // RFO (64B) + writeback (~64B)
    case RW::R70W30:   return 0.7*64.0 + 0.3*128.0;          // ~83.2
    case RW::R50W50:   return 0.5*64.0 + 0.5*128.0;          // 96
  }
  return 64.0;
}

// Tiny PRNG for random access
static inline uint64_t xorshift64(uint64_t& x){
  x ^= x << 13; x ^= x >> 7; x ^= x << 17; return x;
}

static void worker_fn(Work& w) {
  Timer t; t.start();
  volatile uint64_t sink = 0;

  const size_t step  = (w.stride == 0 ? 64 : w.stride);
  const size_t steps = (w.bytes + step - 1) / step;

  if (w.pat == Pat::RANDOM) {
    uint64_t r = w.seed ? w.seed : 0x9e3779b97f4a7c15ull;
    if (w.rw == RW::R) {
      for (size_t it=0; it<w.iters; ++it) {
        for (size_t s=0; s<steps; ++s) {
          size_t off = (xorshift64(r) % steps) * step;
          sink += w.base[off];
        }
      }
    } else if (w.rw == RW::W) {
      for (size_t it=0; it<w.iters; ++it) {
        for (size_t s=0; s<steps; ++s) {
          size_t off = (xorshift64(r) % steps) * step;
          w.base[off] = (uint8_t)it;
        }
      }
    } else if (w.rw == RW::R70W30) {
      for (size_t it=0; it<w.iters; ++it) {
        for (size_t s=0; s<steps; ++s) {
          size_t off = (xorshift64(r) % steps) * step;
          if ((s % 10) < 7) sink += w.base[off];
          else              w.base[off] = (uint8_t)it;
        }
      }
    } else { // 50/50
      for (size_t it=0; it<w.iters; ++it) {
        for (size_t s=0; s<steps; ++s) {
          size_t off = (xorshift64(r) % steps) * step;
          if (s & 1) sink += w.base[off];
          else       w.base[off] = (uint8_t)it;
        }
      }
    }
  } else { // SEQ (stride walk)
    if (w.rw == RW::R) {
      for (size_t it=0; it<w.iters; ++it)
        for (size_t i=0; i<w.bytes; i+=step) sink += w.base[i];
    } else if (w.rw == RW::W) {
      for (size_t it=0; it<w.iters; ++it)
        for (size_t i=0; i<w.bytes; i+=step) w.base[i] = (uint8_t)it;
    } else if (w.rw == RW::R70W30) {
      for (size_t it=0; it<w.iters; ++it) {
        size_t idx = 0;
        for (size_t i=0; i<w.bytes; i+=step, ++idx) {
          if ((idx % 10) < 7) sink += w.base[i];
          else                w.base[i] = (uint8_t)it;
        }
      }
    } else { // 50/50
      for (size_t it=0; it<w.iters; ++it) {
        size_t idx = 0;
        for (size_t i=0; i<w.bytes; i+=step, ++idx) {
          if (idx & 1) sink += w.base[i];
          else         w.base[i] = (uint8_t)it;
        }
      }
    }
  }

  double s = t.stop_s();
  double touches = double(w.iters) * double(steps);
  double bytes_traffic = touches * effective_bytes_per_touch(w.rw);
  w.gbps_out = (bytes_traffic / s) / 1e9;

#if !defined(_WIN32)
  asm volatile(""::"r"(sink):"memory");
#else
  (void)sink;
#endif
}

void run_bandwidth_bench(int argc, char** argv) {
  size_t bytes = 1ULL<<30;      // 1 GiB total region
  int    threads = 1;
  size_t stride = 64;
  RW     rw = RW::R;
  int    cpu0 = -1;
  int    reps = 3;
  size_t iters = 1;
  std::string pattern = "seq"; // CSV compatibility

  for (int i=1; i<argc; ) {
    if      (parse_szt (i,argc,argv,"--bytes",  bytes)) {}
    else if (parse_int (i,argc,argv,"--threads",threads)) {}
    else if (parse_szt (i,argc,argv,"--stride", stride)) {}
    else if (parse_int (i,argc,argv,"--reps",   reps)) {}
    else if (parse_szt (i,argc,argv,"--iters",  iters)) {}
    else if (parse_int (i,argc,argv,"--cpu0",   cpu0)) {}
    else if (parse_flag(i,argc,argv,"--rw=100R") || parse_flag(i,argc,argv,"--rw")) { rw = RW::R; }
    else if (parse_flag(i,argc,argv,"--100R"))  { rw = RW::R; }
    else if (parse_flag(i,argc,argv,"--100W"))  { rw = RW::W; }
    else if (parse_flag(i,argc,argv,"--70R30W")){ rw = RW::R70W30; }
    else if (parse_flag(i,argc,argv,"--50R50W")){ rw = RW::R50W50; }
    else if (parse_flag(i,argc,argv,"--pattern=random")) { pattern = "random"; }
    else if (parse_flag(i,argc,argv,"--pattern=stride")) { pattern = "seq"; } // same loop shape
    else ++i;
  }

  CSV csv;
  csv.set_header("bytes,threads,stride_B,rw,pattern,repetition,GBps,lat_est_ns");

  std::vector<uint8_t> buf(bytes);
  touch_memory(buf.data(), bytes);

  for (int R=0; R<reps; ++R) {
    std::vector<std::thread> th;
    std::vector<Work> works(threads);
    size_t chunk = bytes / size_t(std::max(1,threads));

    for (int k=0; k<threads; ++k) {
      th.emplace_back([&,k](){
        pin_to_cpu(cpu0 < 0 ? -1 : (cpu0 + k));
        works[k] = Work{
          .base     = buf.data() + size_t(k)*chunk,
          .bytes    = chunk,
          .stride   = stride,
          .rw       = rw,
          .iters    = iters,
          .pat      = (pattern=="random" ? Pat::RANDOM : Pat::SEQ),
          .seed     = 0x9e3779b97f4a7c15ull ^ (uint64_t)(R*1315423911u + k*2654435761u),
          .gbps_out = 0.0
        };
        worker_fn(works[k]);
      });
    }
    for (auto& t : th) t.join();

    double gbps_sum = 0.0;
    for (auto& w : works) gbps_sum += w.gbps_out;

    // crude Little's Law proxy: L ≈ inflight bytes / throughput; use chunk as proxy
    double lat_ns = (double)chunk / (gbps_sum * 1e9) * 1e9;

    const char* rwstr =
      (rw==RW::R? "100R" : rw==RW::W? "100W" : rw==RW::R70W30? "70R30W" : "50R50W");

    csv.add_row(std::to_string(bytes)+","+
                std::to_string(threads)+","+
                std::to_string(stride)+","+
                rwstr+"," + pattern + "," +
                std::to_string(R)+","+
                std::to_string(gbps_sum)+","+
                std::to_string(lat_ns));
  }
  csv.print();
}
