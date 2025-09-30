// src/kernel_bench.cpp
#include "util.h"
#include <vector>
#include <cstring>

static void saxpy(float a, const float* x, float* y, size_t n, size_t stride) {
  for (size_t i = 0; i < n; i += stride) {
    y[i] = a * x[i] + y[i];
  }
}

void run_kernel_bench(int argc, char** argv) {
  size_t ws_bytes = 1ULL<<30; // 1 GiB working set
  size_t stride = 1;          // element stride (cache miss control)
  int reps = 3;
  int cpu = -1;
  size_t page_span = 1;       // touch every Nth page to induce DTLB misses
  bool huge = false;
  size_t iters = 5;

  for (int i=1; i<argc; ) {
    if (parse_szt(i,argc,argv,"--ws_bytes", ws_bytes)) {}
    else if (parse_szt(i,argc,argv,"--stride", stride)) {}
    else if (parse_int(i,argc,argv,"--reps", reps)) {}
    else if (parse_int(i,argc,argv,"--cpu", cpu)) {}
    else if (parse_szt(i,argc,argv,"--page_span", page_span)) {}
    else if (parse_flag(i,argc,argv,"--huge")) { huge = true; }
    else if (parse_szt(i,argc,argv,"--iters", iters)) {}
    else ++i;
  }

  pin_to_cpu(cpu);

  size_t n = ws_bytes / sizeof(float);
  std::vector<float> x(n), y(n);
  if (huge) {
    prefer_hugepages(x.data(), n*sizeof(float));
    prefer_hugepages(y.data(), n*sizeof(float));
  }
  for (size_t i=0;i<n;++i){ x[i]=1.0f; y[i]=0.5f; }

  // page-span: force accesses to every Nth page by boosting stride
  if (page_span > 1) {
    const size_t page = 4096;
    size_t extra = (page_span-1)*page/sizeof(float);
    stride += extra;
  }

  CSV csv;
  csv.set_header("ws_bytes,stride_elems,page_span,huge,repetition,sec,GBps_effective");
  for (int R=0; R<reps; ++R) {
    Timer t; t.start();
    for (size_t it=0; it<iters; ++it) {
      saxpy(2.0f, x.data(), y.data(), n, stride);
    }
    double sec = t.stop_s();
    double elemtouched = double((n + stride - 1)/stride) * stride;
    double bytes_moved = double(iters) * elemtouched * 2 * sizeof(float); // read x + read/write y ~ rough
    double gbps = (bytes_moved / sec) / 1e9;
    csv.add_row(std::to_string(ws_bytes)+","+std::to_string(stride)+","+
                std::to_string(page_span)+","+(huge?"1":"0")+","+std::to_string(R)+","+
                std::to_string(sec)+","+std::to_string(gbps));
  }
  csv.print();
}
