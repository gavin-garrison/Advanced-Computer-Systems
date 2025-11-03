#!/usr/bin/env bash
set -euo pipefail

# Requires: gcc, perf, python3, taskset (util-linux)
# Build
make -C "$(dirname "$0")" all

BIN="$(dirname "$0")/bench_a1"
OUTDIR="$(dirname "$0")/results"
mkdir -p "$OUTDIR"

# Common perf counters
CTR="cycles,instructions,cache-misses,LLC-load-misses,branches,branch-misses"

ts() { date +%Y%m%d-%H%M%S; }

echo "=== A1 quick-run start $(ts) ==="

# 1) CPU AFFINITY: pinned vs not pinned jitter comparison
echo "mode,affinity,cpu,iters,time_s" > "$OUTDIR/affinity.csv"
for pin in "-1" "0"; do
  for r in {1..3}; do
    if [ "$pin" = "-1" ]; then
      perf stat -e $CTR -x, --log-fd 3 3>"$OUTDIR/affinity_perf_${r}_nopin.txt" \
        "$BIN" affinity --cpu=-1 --iters=150000000 >> "$OUTDIR/affinity.csv"
    else
      perf stat -e $CTR -x, --log-fd 3 3>"$OUTDIR/affinity_perf_${r}_cpu0.txt" \
        "$BIN" affinity --cpu=0 --iters=150000000 >> "$OUTDIR/affinity.csv"
    fi
  done
done

# 2) THP vs no-THP memcpy throughput
echo "mode,thp,bytes,iters,thp_flag,time_s,GB_copied,GBps" > "$OUTDIR/thp.csv"
for thp in 1 0; do
  perf stat -e $CTR -x, --log-fd 3 3>"$OUTDIR/thp_perf_thp${thp}.txt" \
    "$BIN" thp --bytes=$((512*1024*1024)) --iters=8 --thp=${thp} >> "$OUTDIR/thp.csv"
done

# 3) Prefetcher/stride sensitivity
echo "mode,stride,bytes,strideB,time_s,ns_per_access" > "$OUTDIR/stride.csv"
for s in 64 128 256 512 1024 2048 4096 8192; do
  perf stat -e $CTR -x, --log-fd 3 3>"$OUTDIR/stride_perf_${s}.txt" \
    "$BIN" stride --bytes=$((256*1024*1024)) --stride=${s} >> "$OUTDIR/stride.csv"
done

# 4) SMT interference (pick two CPUs; adjust if your machine has only 2 CPUs)
# Try (0,1) by default. For a stronger effect, place both on siblings.
echo "mode,smt,victim_cpu,interf_cpu,bytes,iters,thp,total_time_s" > "$OUTDIR/smt.csv"
perf stat -e $CTR -x, --log-fd 3 3>"$OUTDIR/smt_perf.txt" \
  "$BIN" smt --victim-cpu=0 --interf-cpu=1 --bytes=$((256*1024*1024)) --iters=150000000 --thp=1 >> "$OUTDIR/smt.csv"

echo "=== Done. Results in $OUTDIR ==="
