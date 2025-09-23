# plot_tail.py
import sys, csv, matplotlib.pyplot as plt
from statistics import median

def main():
    if len(sys.argv) < 6:
        print("Usage: plot_tail.py <csv> <kernel> <dtype> <mode> [--save out.png]")
        sys.exit(1)
    csv_path, kernel, dtype, mode = sys.argv[1:5]
    out = None
    if "--save" in sys.argv:
        out = sys.argv[sys.argv.index("--save")+1]

    vals = {0: [], 1: []}
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("kernel")==kernel and row.get("dtype")==dtype and
                    row.get("vecmode","").upper()==mode.upper()):
                if row.get("label","") not in ("tail",""):
                    pass
                try:
                    tj = int(float(row["tail"]))
                    g = float(row["gflops"])
                    if tj in (0,1): vals[tj].append(g)
                except: pass

    if not (vals[0] or vals[1]):
        print("No rows after filtering. Did you run sweep_tail.ps1?")
        return

    m0 = median(vals[0]) if vals[0] else 0.0
    m1 = median(vals[1]) if vals[1] else 0.0

    plt.figure()
    plt.bar(["tail=0","tail=1"], [m0, m1])
    plt.ylabel("GFLOP/s (median)")
    plt.title(f"Tail handling impact: {kernel} {dtype} ({mode})")
    if out: plt.savefig(out, bbox_inches="tight", dpi=160)
    else: plt.show()

if __name__ == "__main__":
    main()
