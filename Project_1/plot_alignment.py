# plot_alignment.py
import sys, csv, matplotlib.pyplot as plt

def main():
    if len(sys.argv) < 6:
        print("Usage: plot_alignment.py <csv> <kernel> <dtype> <mode> [--save out.png]")
        sys.exit(1)
    csv_path, kernel, dtype, mode = sys.argv[1:5]
    out = None
    if "--save" in sys.argv:
        out = sys.argv[sys.argv.index("--save")+1]

    xs, gflops = [], []
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("kernel")==kernel and row.get("dtype")==dtype and
                    (row.get("vecmode","").upper()==mode.upper())):
                # keep only alignment sweep rows if you labeled them "mis"
                if row.get("label","") not in ("mis","alignment",""):
                    # still allow if user didn’t set label
                    pass
                try:
                    xs.append(int(row["misalign"]))
                    gflops.append(float(row["gflops"]))
                except: pass

    if not xs:
        print("No rows after filtering. Check kernel/dtype/mode and that alignment sweep ran.")
        return

    pts = sorted(zip(xs, gflops))
    xs, gflops = zip(*pts)

    plt.figure()
    plt.plot(xs, gflops, marker="o")
    plt.xlabel("Misalignment (bytes)")
    plt.ylabel("GFLOP/s")
    plt.title(f"Alignment impact: {kernel} {dtype} ({mode})")
    plt.grid(True, alpha=0.3)
    if out: plt.savefig(out, bbox_inches="tight", dpi=160)
    else: plt.show()

if __name__ == "__main__":
    main()
