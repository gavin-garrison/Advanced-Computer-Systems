import sys, re, math
import pandas as pd
import matplotlib.pyplot as plt

def parse_mode_from_hint(hint: str) -> str:
    if not isinstance(hint, str):
        return "UNKNOWN"
    m = re.search(r"mode:([A-Za-z0-9_+\-]+)", hint, flags=re.IGNORECASE)
    return m.group(1).upper() if m else "UNKNOWN"

def coerce_numeric(s):
    return pd.to_numeric(s, errors="coerce")

def filter_unit(df: pd.DataFrame) -> pd.DataFrame:
    # Treat stride/misalign/tail as numeric; tail may be 0/1 or True/False
    stride   = coerce_numeric(df["stride"])
    misalign = coerce_numeric(df["misalign"])
    # tail can be int-ish or bool-ish
    tail_num = coerce_numeric(df["tail"])
    tail_str = df["tail"].astype(str).str.strip().str.lower()
    tail_is_zero = (tail_num.fillna(0) == 0) | (tail_str.isin(["0","false","no","n"]))
    return df[(stride == 1) & (misalign == 0) & (tail_is_zero)]

def main():
    if len(sys.argv) < 6:
        print("Usage: plot_locality.py <csv> <kernel> <dtype> <mode> <gflops|gibps> [--save out.png]")
        sys.exit(1)

    path, kernel, dtype, mode, metric = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].upper(), sys.argv[5].lower()
    out = sys.argv[sys.argv.index("--save")+1] if "--save" in sys.argv else None

    # tolerant read
    df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")

    # ensure columns
    needed = {"kernel","dtype","N","stride","misalign","tail","median_ms","gflops","gibps"}
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print("CSV missing required columns:", missing); sys.exit(1)
    if "hint" not in df.columns: df["hint"] = ""

    df["vecmode"] = df["hint"].apply(parse_mode_from_hint)

    # base filter
    base = df[(df["kernel"] == kernel) & (df["dtype"] == dtype) & (df["vecmode"] == mode)]
    if base.empty:
        print(f"No rows for kernel={kernel}, dtype={dtype}, mode={mode}.")
        # show quick diagnostics
        print("Distinct kernels:", sorted(df["kernel"].dropna().unique().tolist()))
        print("Distinct dtypes:", sorted(df["dtype"].dropna().unique().tolist()))
        print("Distinct modes:", sorted(df["vecmode"].dropna().unique().tolist()))
        sys.exit(1)

    unit = filter_unit(base)
    if unit.empty:
        print("No rows match *unit* filter (stride=1, misalign=0, tail=0/false). Falling back to best-per-N without unit restriction.")
        use = base
    else:
        use = unit

    # choose best (min median_ms) per N
    gb = use.groupby("N")["median_ms"].idxmin()
    best = use.loc[gb].copy().sort_values("N")
    if best.empty:
        print("No rows left after best-per-N selection."); sys.exit(1)

    xs = best["N"].astype(int).tolist()
    if metric == "gflops":
        ys = best["gflops"].astype(float).tolist()
        ylabel = "GFLOP/s"
    elif metric == "gibps":
        ys = best["gibps"].astype(float).tolist()
        ylabel = "GiB/s"
    else:
        print("metric must be gflops or gibps"); sys.exit(1)

    plt.figure()
    plt.plot(xs, ys, marker="o", label=f"{mode} {metric.upper()}")
    plt.xscale("log", base=2)
    plt.xlabel("N (elements)")
    plt.ylabel(ylabel)
    title_detail = "unit-stride/aligned/no-tail" if use is unit else "best-per-N (no unit filter)"
    plt.title(f"Locality — {kernel} {dtype} [{mode}] — {title_detail}")
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.legend()
    if out: plt.savefig(out, dpi=160, bbox_inches="tight")
    else:   plt.show()

if __name__ == "__main__":
    main()
