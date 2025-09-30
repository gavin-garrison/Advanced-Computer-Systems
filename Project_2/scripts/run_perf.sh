#!/usr/bin/env bash
set -euo pipefail
SRC="/mnt/c/Users/Gavin Garrison/CLionProjects/acs/project_2"
BIN="$HOME/memlab-build/memlab"
CPU="0"
mkdir -p "$SRC/results/perf"

EVENTS="task-clock,cycles,instructions,cache-references,cache-misses,dTLB-load-misses"

sudo perf stat -x, -o "$SRC/results/perf/saxpy_local.perf.csv" \
  -e $EVENTS -- taskset -c $CPU "$BIN" kernel --n 67108864 --reps 5 >/dev/null || true

sudo perf stat -x, -o "$SRC/results/perf/saxpy_random.perf.csv" \
  -e $EVENTS -- taskset -c $CPU "$BIN" kernel --n 268435456 --random --reps 5 >/dev/null || true

sudo perf stat -x, -o "$SRC/results/perf/saxpy_tlb_span16.perf.csv" \
  -e $EVENTS -- taskset -c $CPU "$BIN" kernel --ws_bytes 1073741824 --stride 1 --page_span 16 --reps 5 >/dev/null || true

sudo perf stat -x, -o "$SRC/results/perf/saxpy_tlb_span16_huge.perf.csv" \
  -e $EVENTS -- taskset -c $CPU "$BIN" kernel --ws_bytes 1073741824 --stride 1 --page_span 16 --huge --reps 5 >/dev/null || true

echo "perf CSVs saved under results/perf/."
