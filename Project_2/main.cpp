// src/main.cpp
#include "util.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>

void run_latency_bench(int argc, char** argv);
void run_bandwidth_bench(int argc, char** argv);
void run_kernel_bench(int argc, char** argv);

static void usage() {
    puts(
      "memlab — Memory hierarchy experiments\n"
      "Usage:\n"
      "  memlab latency   [options]   # zero-queue, working-set\n"
      "  memlab bw        [options]   # pattern×stride×RW, intensity\n"
      "  memlab kernel    [options]   # cache/TLB impact using SAXPY\n"
      "\nCommon tips: pin with --cpu=N; repeat with --reps=K; CSV to stdout.\n"
    );
}

int main(int argc, char** argv) {
    if (argc < 2) { usage(); return 0; }
    if      (!strcmp(argv[1], "latency"))  run_latency_bench(argc-1, argv+1);
    else if (!strcmp(argv[1], "bw"))       run_bandwidth_bench(argc-1, argv+1);
    else if (!strcmp(argv[1], "kernel"))   run_kernel_bench(argc-1, argv+1);
    else usage();
    return 0;
}
