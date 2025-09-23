# clean_csv.py  (strict, resilient)
import csv, sys, re, io

# canonical header we expect
EXPECTED = [
    "kernel","dtype","N","stride","misalign","tail",
    "median_ms","p10_ms","p90_ms","gflops","gibps","cpe",
    "label","hint","check"
]

inp  = sys.argv[1] if len(sys.argv) > 1 else "results_ascii.csv"
outp = sys.argv[2] if len(sys.argv) > 2 else "results_clean.csv"

# 1) Read raw bytes, strip NULs, decode robustly
raw = open(inp, "rb").read().replace(b"\x00", b"")
for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
    try:
        txt = raw.decode(enc)
        break
    except Exception:
        continue

# normalize newlines
txt = txt.replace("\r\n", "\n").replace("\r", "\n")

# 2) Ensure a header exists; if not, insert our expected header
lines = [ln for ln in txt.split("\n") if ln.strip() != ""]
if not lines or not lines[0].lower().startswith("kernel,"):
    lines.insert(0, ",".join(EXPECTED))

# 3) Parse and build STRICT rows (ignore unknown columns completely)
reader = csv.DictReader(io.StringIO("\n".join(lines)))
rows = []
for r in reader:
    # skip stray header lines that appeared mid-file
    if (r.get("kernel","").lower() == "kernel") or (not r.get("kernel")):
        continue

    # build a clean row with only EXPECTED keys
    clean = {k: (r.get(k) or "").strip() for k in EXPECTED}

    # vecmode from hint
    hint = clean.get("hint","")
    m = re.search(r"mode:([A-Za-z0-9_+\-]+)", hint, re.IGNORECASE)
    clean["vecmode"] = m.group(1).upper() if m else "UNKNOWN"

    # coerce types (best effort)
    def as_int(x):
        try: return int(float(x))
        except: return x
    def as_float(x):
        try: return float(x)
        except: return x

    for k in ("N","stride","misalign","tail"):
        clean[k] = as_int(clean[k])
    for k in ("median_ms","p10_ms","p90_ms","gflops","gibps","cpe","check"):
        clean[k] = as_float(clean[k])

    rows.append(clean)

# 4) Write back with a fixed schema
fieldnames = EXPECTED + ["vecmode"]
with open(outp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)

print(f"Wrote {outp} with {len(rows)} rows and strict columns: {fieldnames}")
