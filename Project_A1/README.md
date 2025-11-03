# Project A1 — Fast Path (WSL/Linux)

This is a *minimal* end-to-end setup to finish A1 quickly with solid, reproducible results.

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

## Notes
- If THP is disabled on your system, you can try:
  - `cat /sys/kernel/mm/transparent_hugepage/enabled`
  - Use `sudo` to toggle if allowed, or just report the observed behavior and note the system policy.
- If you have only 2 logical CPUs, SMT test still runs but interference magnitude may vary.
- For the report: include CPU model (`/proc/cpuinfo`), kernel (`uname -a`), GCC version, and WSL version.

## Re-run knobs
Edit `run.sh` to change byte sizes, iters, and target CPUs.

## Suggested report outline
- Setup: machine/OS/compiler + command snippets
- Methodology: describe 4 features and what we varied
- Results: 3–4 plots above + short table snippets from CSV
- Insights: 1–2 bullets per feature tying to OS/µarch principles
- Limitations: WSL vs bare metal, THP policy, small core counts, etc.
