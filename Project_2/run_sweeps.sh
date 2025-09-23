#!/usr/bin/env bash
set -euo pipefail

SRC="/mnt/c/Users/Gavin Garrison/CLionProjects/acs/project_2"
BIN="$HOME/memlab-build/memlab"      # built on ext4
CPU="0"                              # single-thread pin
THREADSET="0-7"                      # adjust to your cores

mkdir -p "$SRC/results"/{lat,bw,kernel,perf,mlc}

echo "[build]"
cmake -S "$SRC" -B "$HOME/memlab-build" -G Ninja -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build "$HOME/memlab-build" -j >/dev/null

# 1) Zero-queue latency vs working set
echo "[1/7] latency sweep (8KB→512MB)"
taskset -c $CPU "$BIN" latency \
  --min_kb 8 --max_mb 512 --stride 64 --iters 5000000 --reps 5 \
  > "$SRC/results/lat/latency_ws.csv"

# 2) Pattern × stride (seq/random × 64/256/1024B) 100% reads
echo "[2/7] pattern × stride"
for S in 64 256 1024; do
  for PAT in seq random; do
    taskset -c $CPU "$BIN" bw --bytes 536870912 --threads 1 --stride $S --reps 5 --100R \
      $( [[ $PAT == random ]] && echo --pattern=random ) \
      > "$SRC/results/bw/bw_${PAT}_${S}_100R.csv"
  done
done

# 3) Read/Write mix @64B
echo "[3/7] R/W mix"
for MIX in 100R 100W 70R30W 50R50W; do
  taskset -c $CPU "$BIN" bw --bytes 536870912 --threads 1 --stride 64 --reps 5 --$MIX \
    > "$SRC/results/bw/mix_${MIX}.csv"
done

# 4) Intensity sweep (throughput vs threads)
echo "[4/7] intensity sweep"
for T in 1 2 4 8; do
  taskset -c $THREADSET "$BIN" bw --bytes 1073741824 --threads $T --stride 64 --reps 5 --100R \
    > "$SRC/results/bw/intensity_T${T}.csv"
done

# 5) Working-set transitions covered by (1).

# 6) Kernel microbenchmark (cache-miss impact)
echo "[6/7] kernel cache-miss impact"
taskset -c $CPU "$BIN" kernel --n 67108864  --reps 5 > "$SRC/results/kernel/saxpy_local.csv"
taskset -c $CPU "$BIN" kernel --n 268435456 --random --reps 5 > "$SRC/results/kernel/saxpy_random.csv"

# 7) TLB impact (page_span + huge)
echo "[7/7] kernel TLB impact"
taskset -c $CPU "$BIN" kernel --ws_bytes 1073741824 --stride 1 --page_span 16 --reps 5 \
  > "$SRC/results/kernel/saxpy_tlb_span16.csv"
taskset -c $CPU "$BIN" kernel --ws_bytes 1073741824 --stride 1 --page_span 16 --huge --reps 5 \
  > "$SRC/results/kernel/saxpy_tlb_span16_huge.csv"

echo "All sweeps complete. CSVs in results/."
