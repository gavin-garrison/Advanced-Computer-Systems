import os, glob, re
import pandas as pd

CSV = "results/csv"
os.makedirs(CSV, exist_ok=True)

def write_if(df, path):
    if df is not None and not df.empty:
        df.to_csv(path, index=False)
        print("wrote", path)

# --- 0) zero-queue: try to find per-level latency table and add cycles later
cand = [p for p in glob.glob(f"{CSV}/*.csv") if re.search(r"zeroq|baseline|idle.*lat", p, re.I)]
if cand:
    df = pd.read_csv(cand[0])
    # normalize columns
    if {"Level","Read_ns"}.issubset(df.columns): df = df.rename(columns=str.lower)
    if {"level","read_ns"}.issubset(df.columns):
        write_if(df[["level","read_ns"] + ([c for c in df.columns if c=="write_ns"])],
                 f"{CSV}/zeroq_latencies.csv")

# --- 1) pattern×stride aggregate -> pattern_stride_all.csv
# Accepts files that look like: stride_B, seq_GBs, rand_GBs  (bandwidth)
# or long form with columns: pattern,stride_B,bandwidth_GBs or latency_ns
ps_out_rows = []
for p in glob.glob(f"{CSV}/*.csv"):
    name = os.path.basename(p).lower()
    df = pd.read_csv(p)
    cols = set(map(str.lower, df.columns))
    # wide bandwidth table
    if {"stride_b","seq_gbs","rand_gbs"}.issubset(cols):
        d = df.rename(columns=str.lower)
        for patt in ["seq","rand"]:
            ps_out_rows += [{"pattern":patt,"stride_B":int(r["stride_b"]),
                             "metric":"bandwidth_GBs","value":float(r[f"{patt}_gbs"]), "run_id":1}
                            for _,r in d.iterrows()]
    # long form bandwidth/latency
    elif {"pattern","stride_b","metric","value"}.issubset(cols):
        d = df.rename(columns=str.lower)
        if set(d["metric"]).intersection({"bandwidth_gbs","latency_ns"}):
            for _,r in d.iterrows():
                ps_out_rows.append(dict(pattern=r["pattern"],stride_B=int(r["stride_b"]),
                                        metric=r["metric"], value=float(r["value"]), run_id=int(r.get("run_id",1))))
if ps_out_rows:
    write_if(pd.DataFrame(ps_out_rows), f"{CSV}/pattern_stride_all.csv")

# --- 2) R/W mix -> rw_mix_all.csv  (expects: rw_mix, bandwidth_GBs, run_id)
for p in glob.glob(f"{CSV}/*.csv"):
    df = pd.read_csv(p)
    cols = set(map(str.lower, df.columns))
    if {"mix","gbs"}.issubset(cols) or {"rw_mix","bandwidth_gbs"}.issubset(cols):
        d = df.rename(columns={c:c.lower() for c in df.columns})
        d = d.rename(columns={"mix":"rw_mix","gbs":"bandwidth_gbs"})
        if "run_id" not in d: d["run_id"] = 1
        write_if(d[["rw_mix","bandwidth_gbs","run_id"]], f"{CSV}/rw_mix_all.csv")
        break

# --- 3) intensity (loaded latency) -> intensity_loaded_latency.csv
# Accept inputs like: threads, loaded_latency_ns, throughput_GBs
for p in glob.glob(f"{CSV}/*.csv"):
    df = pd.read_csv(p)
    cols = {c.lower() for c in df.columns}
    # try common variants: latency_ns, load_latency, tput_GBs, bw_GBs
    if {"threads"}.issubset(cols) and ({"loaded_latency_ns"}<=cols or {"latency_ns"}<=cols) \
       and ({"throughput_gbs"}<=cols or {"bw_gbs"}<=cols or {"bandwidth_gbs"}<=cols):
        d = df.rename(columns={c:c.lower() for c in df.columns})
        if "loaded_latency_ns" not in d and "latency_ns" in d:
            d["loaded_latency_ns"] = d["latency_ns"]
        for alt in ["bw_gbs","bandwidth_gbs"]:
            if alt in d: d["throughput_gbs"] = d[alt]
        if "run_id" not in d: d["run_id"] = 1
        write_if(d[["threads","loaded_latency_ns","throughput_gbs","run_id"]],
                 f"{CSV}/intensity_loaded_latency.csv")
        break

# --- 4) working-set latency sweep -> latency_vs_wss.csv
for p in glob.glob(f"{CSV}/*.csv"):
    df = pd.read_csv(p)
    cols = {c.lower() for c in df.columns}
    if {"working_set_b","latency_ns"}.issubset(cols):
        d = df.rename(columns={c:c.lower() for c in df.columns})
        if "run_id" not in d: d["run_id"] = 1
        write_if(d[["working_set_b","latency_ns","run_id"]], f"{CSV}/latency_vs_wss.csv")
        break

print("harvest: done")
