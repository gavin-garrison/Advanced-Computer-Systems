import pathlib, re, pandas as pd

CWD  = pathlib.Path(".").resolve()
ROOT = (CWD/"results") if (CWD/"results").is_dir() else CWD  # works from root or from results/
if (ROOT.name!="results") and (ROOT/"results").is_dir():
    ROOT = ROOT/"results"
OUT  = ROOT/"csv"
OUT.mkdir(parents=True, exist_ok=True)

def read_df(p):
    try:
        return pd.read_csv(p, sep="\t" if p.suffix.lower()==".tsv" else ",")
    except Exception as e:
        print("  ! read error:", e, "->", p); return None

print("== scanning ==", ROOT)
cands = []
for sub in ("mlc","kernel","bw","lat","perf","raw","csv"):
    d = ROOT/sub
    if d.exists():
        cands += list(d.rglob("*.csv")) + list(d.rglob("*.tsv"))

def cols_lower(df): return {c.lower():c for c in df.columns}

hits = dict(zeroq=False, pattern_stride=False, rw_mix=False, intensity=False,
            wss=False, cache_perf=False, tlb_perf=False)

for p in sorted(cands):
    df = read_df(p)
    if df is None or df.empty: continue
    L = cols_lower(df)
    print(f"- {p.relative_to(ROOT)}  cols={list(df.columns)[:8]} rows={len(df)}")

    # zero-queue latencies
    if not hits["zeroq"]:
        lvl = L.get("level") or L.get("cache_level") or L.get("tier")
        rns = L.get("read_ns") or L.get("read (ns)") or L.get("latency_ns") or L.get("lat_ns")
        wns = L.get("write_ns") or L.get("write (ns)")
        if lvl and rns:
            out = df[[lvl,rns]].rename(columns={lvl:"level", rns:"read_ns"})
            if wns: out["write_ns"] = df[wns]
            out.to_csv(OUT/"zeroq_latencies.csv", index=False); hits["zeroq"]=True; continue

    # pattern×stride (long form)
    if not hits["pattern_stride"]:
        if {"pattern","stride_b","metric","value"}.issubset(L):
            out = df.rename(columns={L["pattern"]:"pattern", L["stride_b"]:"stride_B",
                                     L["metric"]:"metric",   L["value"]:"value"})
            if "run_id" not in out: out["run_id"]=1
            out[["pattern","stride_B","metric","value","run_id"]].to_csv(OUT/"pattern_stride_all.csv", index=False)
            hits["pattern_stride"]=True; continue
        # wide bandwidth with seq/random columns
        if "stride_b" in L:
            bwcols = [k for k in L if re.search(r"(seq|sequential).*gbs|rand.*gbs|random.*gbs", k)]
            if bwcols:
                stride = df[L["stride_b"]].astype(int)
                rows=[]
                for k in bwcols:
                    patt = "seq" if "seq" in k else "random"
                    vals = df[L[k]].astype(float)
                    rows += [dict(pattern=patt, stride_B=int(s), metric="bandwidth_GBs",
                                  value=float(v), run_id=1) for s,v in zip(stride, vals)]
                pd.DataFrame(rows).to_csv(OUT/"pattern_stride_all.csv", index=False)
                hits["pattern_stride"]=True; continue

    # R/W mix
    if not hits["rw_mix"]:
        bwc = L.get("bandwidth_gbs") or L.get("gbs") or L.get("bw_gbs") or L.get("throughput_gbs")
        if "rw_mix" in L and bwc:
            out = df.rename(columns={L["rw_mix"]:"rw_mix", bwc:"bandwidth_GBs"})
            if "run_id" not in out: out["run_id"]=1
            out[["rw_mix","bandwidth_GBs","run_id"]].to_csv(OUT/"rw_mix_all.csv", index=False)
            hits["rw_mix"]=True; continue

    # intensity
    if not hits["intensity"]:
        if "threads" in L:
            latc = L.get("loaded_latency_ns") or L.get("latency_ns") or L.get("loaded_ns") or L.get("lat_ns")
            thc  = L.get("throughput_gbs") or L.get("tput_gbs") or L.get("bw_gbs") or L.get("bandwidth_gbs")
            if latc and thc:
                out = df.rename(columns={L["threads"]:"threads", latc:"loaded_latency_ns", thc:"throughput_GBs"})
                if "run_id" not in out: out["run_id"]=1
                out[["threads","loaded_latency_ns","throughput_GBs","run_id"]].to_csv(OUT/"intensity_loaded_latency.csv", index=False)
                hits["intensity"]=True; continue

    # working set
    if not hits["wss"]:
        w = L.get("working_set_b") or L.get("wss_b") or L.get("footprint_b") or L.get("size_b") or L.get("bytes")
        l = L.get("latency_ns") or L.get("lat_ns") or L.get("read_lat_ns")
        if w and l:
            out = df.rename(columns={w:"working_set_B", l:"latency_ns"})
            if "run_id" not in out: out["run_id"]=1
            out[["working_set_B","latency_ns","run_id"]].to_csv(OUT/"latency_vs_wss.csv", index=False)
            hits["wss"]=True; continue

    # perf → cache kernel
    if not hits["cache_perf"]:
        if {"cycles","instructions"}.issubset(L) and any(k in L for k in ("llc-load-misses","llc_misses")) \
           and any(k in L for k in ("size_b","size","working_set_b")) and any(k in L for k in ("stride_b","stride")):
            S  = L.get("size_b") or L.get("size") or L.get("working_set_b")
            ST = L.get("stride_b") or L.get("stride")
            LM = L.get("llc-load-misses") or L.get("llc_misses")
            out = df.rename(columns={S:"size_B", ST:"stride_B", LM:"llc_misses", L["cycles"]:"cycles", L["instructions"]:"instr"})
            if "run_id" not in out: out["run_id"]=1
            out[["size_B","stride_B","run_id","cycles","instr","llc_misses"]].to_csv(OUT/"cache_kernel_perf.csv", index=False)
            hits["cache_perf"]=True; continue

    # perf → TLB kernel
    if not hits["tlb_perf"]:
        if {"cycles","instructions"}.issubset(L) and any(k in L for k in ("dtlb-load-misses","dtlb_misses")) \
           and any(k in L for k in ("size_b","size")) and any(k in L for k in ("hugepages","thp","hp")):
            S  = L.get("size_b") or L.get("size")
            HP = L.get("hugepages") or L.get("thp") or L.get("hp")
            DM = L.get("dtlb-load-misses") or L.get("dtlb_misses")
            out = df.rename(columns={S:"size_B", HP:"hugepages", DM:"dtlb_load_misses", L["cycles"]:"cycles", L["instructions"]:"instr"})
            if "run_id" not in out: out["run_id"]=1
            out[["size_B","hugepages","run_id","cycles","instr","dtlb_load_misses"]].to_csv(OUT/"tlb_kernel_perf.csv", index=False)
            hits["tlb_perf"]=True; continue

print("summary:", hits)
print("canonical outputs ->", OUT)
