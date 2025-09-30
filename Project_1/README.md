The project report PDF contains all of the gradeable points I was able to hit.
https://github.com/gavin-garrison/Advanced-Computer-Systems/blob/main/Project_1/Project%201%20Report%20(1).pdf

Code and PNGs are also found in this repo
# Project 1 — Vector Kernels: Alignment, Stride, Locality, Roofline & Tails

This project profiles simple vector kernels (dot, mul, SAXPY, stencil) to study:
- **Alignment** effects (scalar vs SIMD, AVX2),
- **Stride** (spatial locality & prefetching),
- **Working-set locality** (cache → DRAM transitions),
- **Roofline** (compute vs bandwidth limits),
- **Tail latency** behavior across runs.

All raw/cleaned CSVs, scripts, and figures are in this folder for full reproducibility.

---

## Contents


