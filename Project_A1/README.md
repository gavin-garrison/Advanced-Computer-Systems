# Project A1

## Features covered (4/4)
1. **CPU Affinity / Scheduling** — pinned vs not pinned jitter
2. **SMT Interference** — victim memcpy vs interferer compute on sibling vs separate CPUs
3. **Transparent Huge Pages (THP)** — memcpy throughput with/without `MADV_HUGEPAGE`
4. **Prefetcher/Stride Effects** — `ns/access` vs stride (64B → 8KB)

## Quick Start (WSL / Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y build-essential linux-tools-common linux-tools-generic linux-tools-`uname -r` python3 python3-pip
cd A1-fast
make
bash run.sh
python3 plot.py
```

Results & plots appear in `results/`:
- `affinity.csv`, `affinity_box.png`
- `thp.csv`, `thp_bar.png`
- `stride.csv`, `stride_line.png`
- `smt.csv` (+ perf text files for each run)

To discover SMT sibling pairs (for better interference tests):
```bash
bash siblings.sh
```

## Perf counters
The `run.sh` script uses:
```
cycles,instructions,cache-misses,LLC-load-misses,branches,branch-misses
```
Each experiment also writes a corresponding `*_perf_*.txt` with raw perf output.

## Re-run knobs
Edit `run.sh` to change byte sizes, iters, and target CPUs.
