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
## Rebuild or regenerate plots


# from Project_1/
python3 -m pip install --user pandas numpy matplotlib

# normalize raw → cleaned CSV (if needed)
python3 clean_csv.py

# plot script usage:
# Usage: plot_alignment.py <csv> <kernel> <dtype> <mode> [--save out.png]

# examples (adjust args to your CSV schema):
python3 plot_alignment.py results_clean.csv saxpy f32 simd      --save alignment_all.png
python3 plot_stride.py     results_clean.csv                    # writes stride_*.png
python3 plot_locality.py   results_clean.csv                    # writes locality_*.png
python3 plot_roofline.py   results_clean.csv                    # writes roofline_*.png
python3 plot_tail.py       results_clean.csv                    # writes tail_*.png





## Figures

true{f}](./align_saxpy_f32_AVX2.png)
true{f}](./alignment_all.png)
true{f}](./locality_saxpy_f32_AVX2.png)
true{f}](./locality_saxpy_f32_AVX2_gibps.png)
true{f}](./locality_saxpy_f32_annotated.png)
true{f}](./locality_saxpy_f32_simd.png)
true{f}](./locality_saxpy_f32_simd_cpe.png)
true{f}](./locality_saxpy_f32_simd_gibps.png)
true{f}](./roofline_saxpy_f32_AVX2.png)
true{f}](./roofline_saxpy_f32_simd.png)
true{f}](./speedup_dot_f32.png)
true{f}](./speedup_dot_f64.png)
true{f}](./speedup_f32.png)
true{f}](./speedup_f64.png)
true{f}](./speedup_mul_f32.png)
true{f}](./speedup_mul_f64.png)
true{f}](./speedup_saxpy_f32.png)
true{f}](./speedup_saxpy_f64.png)
true{f}](./speedup_stencil_f32.png)
true{f}](./speedup_stencil_f64.png)
true{f}](./stride_all.png)
true{f}](./stride_dot_f32_AVX2.png)
true{f}](./stride_dot_f32_N1048576.png)
true{f}](./tail_all.png)
true{f}](./tail_mul_f64_AUTO.png)
