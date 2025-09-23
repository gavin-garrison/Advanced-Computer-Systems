import sys, re, numpy as np, pandas as pd, matplotlib.pyplot as plt

def parse_mode_from_hint(hint: str) -> str:
    if not isinstance(hint, str):
        return "UNKNOWN"
    m = re.search(r"mode:([A-Za-z0-9_+\-]+)", hint, flags=re.IGNORECASE)
    return m.group(1).upper() if m else "UNKNOWN"

def coerce_numeric(s):
    return pd.to_numeric(s, errors="coerce")

def filter_unit(df: pd.DataFrame) -> pd.DataFrame:
    stride   = coerce_numeric(df["stride"])
    misalign = coerce_numeric(df["misalign"])
    tail_num = coerce_numeric(df["tail"])
    tail_str = df["tail"].astype(str).str.strip().str.lower()
    tail_is_zero = (tail_num.fillna(0) == 0) | (tail_str.isin(["0","false","no","n"]))
    return df[(stride == 1) & (misalign == 0) & (tail_is_zero)]

def main():
    if len(sys.argv) < 8:
        print("Usage: plot_roofline.py <csv> <kernel> <dtype> <mode> <peakGF> <memGiBps> [--save out.png]")
        sys.exit(1)

    path, kernel, dtype, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].upper()
    peakGF, memBW = float(sys.argv[5]), float(sys.argv[6])
    out = sys.argv[sys.argv.index("--save")+1] if "--save" in sys.argv else None

    df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")

    needed = {"kernel","dtype","N","stride","misalign","tail","median_ms","gflops","gibps"}
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print("CSV missing required columns:", missing); sys.exit(1)
    if "hint" not in df.columns: df["hint"] = ""

    df["vecmode"] = df["hint"].apply(parse_mode_from_hint)

    base = df[(df["kernel"] == kernel) & (df["dtype"] == dtype) & (df["vecmode"] == mode)]
    if base.empty:
        print(f"No rows for kernel={kernel}, dtype={dtype}, mode={mode}.")
        print("Distinct kernels:", sorted(df["kernel"].dropna().unique().tolist()))
        print("Distinct dtypes:", sorted(df["dtype"].dropna().unique().tolist()))
        print("Distinct modes:", sorted(df["vecmode"].dropna().unique().tolist()))
        sys.exit(1)

    unit = filter_unit(base)
    use = unit if not unit.empty else base
    if unit.empty:
        print("No rows match *unit* filter; roofline will use best-per-N without unit restriction.")

    # best (min time) per N
    idx = use.groupby("N")["median_ms"].idxmin()
    best = use.loc[idx].copy().sort_values("N")
    if best.empty:
        print("No rows left after best-per-N selection."); sys.exit(1)

    # Arithmetic intensity ≈ FLOPs/Byte = (GFLOP/s*1e9) / (GiB/s * 1024^3)
    ai = (best["gflops"].astype(float) * 1e9) / (best["gibps"].astype(float) * (1024.0 ** 3) + 1e-30)
    perf = best["gflops"].astype(float)

    # roofline curve: min(peakGF, memBW * AI)
    xs = np.logspace(-3, 3, 256)
    roof = np.minimum(peakGF, memBW * xs)

    plt.figure()
    plt.loglog(xs, roof, label=f"Roofline (peak={peakGF} GF/s, mem={memBW} GiB/s)")
    plt.scatter(ai, perf, s=24, label=f"{mode} results")
    title_detail = "unit-stride/aligned/no-tail" if use is unit else "best-per-N (no unit filter)"
    plt.title(f"Roofline — {kernel} {dtype} [{mode}] — {title_detail}")
    plt.xlabel("Arithmetic Intensity (FLOPs / Byte)")
    plt.ylabel("GFLOP/s (achieved)")
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.legend()
    if out: plt.savefig(out, dpi=160, bbox_inches="tight")
    else:   plt.show()

if __name__ == "__main__":
    main()
