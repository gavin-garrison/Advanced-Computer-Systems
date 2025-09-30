import os, re, glob, pathlib
import pandas as pd

ROOT = pathlib.Path(".").resolve()
CSV_OUT = ROOT/"results/csv"
CSV_OUT.mkdir(parents=True, exist_ok=True)

def sniff_csvs():
    pats = ["**/*.csv","**/*.tsv"]
    skip = re.compile(r"/(build|cmake-build-|\.venv|\.git)/")
    files=[]
    for pat in pats:
        for p in ROOT.glob(pat):
            if skip.search(str(p)): continue
            files.append(p)
    return files

def read_any(p):
    try:
        if p.suffix.lower()==".tsv":
            return pd.read_csv(p, sep="\t")
        return pd.read_csv(p)
    except Exception:
        return None

def write_if(df, path):
    if df is not None and not df.empty:
        df.to_csv(path, index=False)
        print("wrote", path)
        return True
    return False

# ---------- 0) zero-queue latencies ----------
def try_zeroq(df):
    cols = {c.strip().lower(): c for c in df.columns}
    have_level = any(k in cols for k in ["level","cache_level","tier"])
    have_read  = any(k in cols for k in ["read_ns","read (ns)","latency_ns","lat_ns"])
    if have_level and have_read:
        L = cols.get("level") or cols.get("cache_level") or cols.get("tier")
        R = cols.get("read_ns") or cols.get("read (ns)") or cols.get("latency_ns") or cols.get("lat_ns")
        W = cols.get("write_ns") or cols.get("write (ns)")
        out = df[[L,R]].rename(columns={L:"level",R:"read_ns"})
        if W: out["write_ns"] = df[W]
        return write_if(out, CSV_OUT/"zeroq_latencies.csv")
    return False

# ---------- 1) pattern×stride (long form or wide seq/rand) ----------
def try_pattern_stride(df):
    cols = {c.lower():c for c in df.columns}
    # long form
    if {"pattern","stride_b","metric","value"} <= set(cols):
        out = df.rename(columns={cols["pattern"]:"pattern",
                                 cols["stride_b"]:"stride_B",
                                 cols["metric"]:"metric",
                                 cols["value"]:"value"})
        if "run_id" not in out: out["run_id"]=1
        return write_if(out[["pattern","stride_B","metric","value","run_id"]],
                        CSV_OUT/"pattern_stride_all.csv")
    # wide bandwidth: stride_B, seq_GBs, rand_GBs
    if {"stride_b","seq_gbs","rand_gbs"} <= set(cols):
        stride = df[cols["stride_b"]].astype(int)
        rows=[]
        for patt,col in [("seq","seq_gbs"),("random","rand_gbs")]:
            vals = df[cols[col]].astype(float)
            rows += [{"pattern":patt,"stride_B":int(s),"metric":"bandwidth_GBs","value":float(v),"run_id":1}
                     for s,v in zip(stride, vals)]
        return write_if(pd.DataFrame(rows), CSV_OUT/"pattern_stride_all.csv")
    return False

# ---------- 2) R/W mix ----------
def try_rw_mix(df):
    cols = {c.lower():c for c in df.columns}
    if "rw_mix" in cols and any(k in cols for k in ["bandwidth_gbs","gbs","bw_gbs"]):
        bwc = cols.get("bandwidth_gbs") or cols.get("gbs") or cols.get("bw_gbs")
        out = df.rename(columns={cols["rw_mix"]:"rw_mix", bwc:"bandwidth_GBs"})
        if "run_id" not in out: out["run_id"]=1
        return write_if(out[["rw_mix","bandwidth_GBs","run_id"]], CSV_OUT/"rw_mix_all.csv")
    # fallback: read_pct/write_pct + bandwidth_gbs
    if {"read_pct","write_pct","bandwidth_gbs"} <= set(cols):
        lab = df[cols["read_pct"]].astype(int).astype(str)+"R"+df[cols["write_pct"]].astype(int).astype(str)+"W"
        out = pd.DataFrame({"rw_mix":lab, "bandwidth_GBs":df[cols["bandwidth_gbs"]].astype(float), "run_id":1})
        return write_if(out, CSV_OUT/"rw_mix_all.csv")
    return False

# ---------- 3) intensity (loaded latency) ----------
def try_intensity(df):
    cols = {c.lower():c for c in df.columns}
    if "threads" not in cols: return False
    latc = cols.get("loaded_latency_ns") or cols.get("latency_ns") or cols.get("loaded_ns") or cols.get("lat_ns")
    thc  = cols.get("throughput_gbs") or cols.get("tput_gbs") or cols.get("bw_gbs") or cols.get("bandwidth_gbs")
    if not (latc and thc): return False
    out = df.rename(columns={cols["threads"]:"threads", latc:"loaded_latency_ns", thc:"throughput_GBs"})
    if "run_id" not in out: out["run_id"]=1
    return write_if(out[["threads","loaded_latency_ns","throughput_GBs","run_id"]],
                    CSV_OUT/"intensity_loaded_latency.csv")

# ---------- 4) working-set latency sweep ----------
def try_wss(df):
    cols = {c.lower():c for c in df.columns}
    w = cols.get("working_set_b") or cols.get("wss_b") or cols.get("footprint_b") or cols.get("size_b") or cols.get("bytes")
    l = cols.get("latency_ns") or cols.get("lat_ns") or cols.get("read_lat_ns")
    if not (w and l): return False
    out = df.rename(columns={w:"working_set_B", l:"latency_ns"})
    if "run_id" not in out: out["run_id"]=1
    return write_if(out[["working_set_B","latency_ns","run_id"]],
                    CSV_OUT/"latency_vs_wss.csv")

# ---------- 5) perf logs → cache_kernel_perf.csv ----------
def harvest_perf_logs():
    rows=[]
    for f in ROOT.glob("results/raw/perf/s*_st*_r*.perf"):
        b=f.name
        m=re.match(r"s(\d+)_st(\d+)_r(\d+)\.perf", b)
        if not m: continue
        size,stride,run=map(int,m.groups())
        txt=f.read_text()
        def get(ev):
            mm=re.search(rf"([0-9,]+),{re.escape(ev)},", txt)
            return int(mm.group(1).replace(",","")) if mm else None
        rows.append(dict(size_B=size,stride_B=stride,run_id=run,
                         cycles=get("cycles"),
                         instr=get("instructions"),
                         llc_misses=get("LLC-load-misses")))
    if rows:
        return write_if(pd.DataFrame(rows), CSV_OUT/"cache_kernel_perf.csv")
    return False

# ---------- 6) perf logs → tlb_kernel_perf.csv ----------
def harvest_tlb_logs():
    rows=[]
    for f in ROOT.glob("results/raw/perf/s*_hp*_r*.perf"):
        b=f.name
        m=re.match(r"s(\d+)_hp(on|off)_r(\d+)\.perf", b)
        if not m: continue
        size,hp,run=m.groups(); size,run=int(size),int(run)
        txt=f.read_text()
        def get(ev):
            mm=re.search(rf"([0-9,]+),{re.escape(ev)},", txt)
            return int(mm.group(1).replace(",","")) if mm else None
        rows.append(dict(size_B=size, hugepages=hp, run_id=run,
                         cycles=get("cycles"),
                         instr=get("instructions"),
                         dtlb_load_misses=get("dTLB-load-misses")))
    if rows:
        return write_if(pd.DataFrame(rows), CSV_OUT/"tlb_kernel_perf.csv")
    return False

hits = {"zeroq":False,"ps":False,"rw":False,"int":False,"wss":False}
for p in sniff_csvs():
    df = read_any(p)
    if df is None or df.empty: continue
    if not hits["zeroq"]: hits["zeroq"]=try_zeroq(df)
    if not hits["ps"]:    hits["ps"]=try_pattern_stride(df)
    if not hits["rw"]:    hits["rw"]=try_rw_mix(df)
    if not hits["int"]:   hits["int"]=try_intensity(df)
    if not hits["wss"]:   hits["wss"]=try_wss(df)

hits["cache_perf"]=harvest_perf_logs()
hits["tlb_perf"]=harvest_tlb_logs()

print("harvest summary:", hits)
print("outputs in", CSV_OUT)
