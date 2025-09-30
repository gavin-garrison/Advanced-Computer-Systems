import os, re, glob, pathlib
import pandas as pd

ROOT = pathlib.Path("results").resolve()
OUT  = ROOT/"csv"
OUT.mkdir(parents=True, exist_ok=True)

def read_df(p):
    try:
        if p.suffix.lower()==".tsv": return pd.read_csv(p, sep="\t")
        return pd.read_csv(p)
    except Exception as e:
        print("  ! read error:", e, "->", p)
        return None

def ls_cols(p):
    df = read_df(p)
    if df is None or df.empty: return None, []
    cols = list(df.columns)
    print(f"  - {p.relative_to(ROOT)}  cols={cols[:8]}{'...' if len(cols)>8 else ''}  rows={len(df)}")
    return df, [c.strip().lower() for c in cols]

print("== scanning ==", ROOT)
cands = []
for sub in ("mlc","kernel","bw","lat","perf","raw","csv"):
    d = ROOT/sub
    if d.exists():
        cands += list(d.rglob("*.csv")) + list(d.rglob("*.tsv"))

# buckets for canonical outputs
zeroq_written = False
ps_written    = False
rw_written    = False
int_written   = False
wss_written   = False
cache_written = False
tlb_written   = False

# helper to write once
def write_once(flag_name, df, name):
    global zeroq_written,ps_written,rw_written,int_written,wss_written,cache_written,tlb_written
    if df is None or df.empty: return False
    if locals()[flag_name]:    return False
    outp = OUT/name
    df.to_csv(outp, index=False)
    print("  -> wrote", outp)
    locals()[flag_name] = True
    globals()[flag_name] = True
    return True

# pass 1: inspect and opportunistically map
for p in sorted(cands):
    print(f"\nfile: {p.relative_to(ROOT)}")
    df, low = ls_cols(p)
    if df is None: continue

    lowmap = {c.lower():c for c in df.columns}

    # ----- zero-queue latencies (MLC/idle lat)
    if not zeroq_written:
        has_level = any(k in low for k in ("level","cache_level","tier"))
        has_read  = any(k in low for k in ("read_ns","read (ns)","latency_ns","lat_ns"))
        if has_level and has_read:
            L = lowmap.get("level") or lowmap.get("cache_level") or lowmap.get("tier")
            R = lowmap.get("read_ns") or lowmap.get("read (ns)") or lowmap.get("latency_ns") or lowmap.get("lat_ns")
            W = lowmap.get("write_ns") or lowmap.get("write (ns)")
            out = df[[L,R]].rename(columns={L:"level",R:"read_ns"})
            if W: out["write_ns"] = df[W]
            write_once("zeroq_written", out, "zeroq_latencies.csv"); continue

    # ----- pattern × stride (seq/random bandwidth & latency)
    if not ps_written:
        # long form: pattern,stride_B,metric,value,(run_id)
        if {"pattern","stride_b","metric","value"} <= set(low):
            out = df.rename(columns={lowmap["pattern"]:"pattern",
                                     lowmap["stride_b"]:"stride_B",
                                     lowmap["metric"]:"metric",
                                     lowmap["value"]:"value"})
            if "run_id" not in out: out["run_id"]=1
            write_once("ps_written", out[["pattern","stride_B","metric","value","run_id"]],
                       "pattern_stride_all.csv"); continue
        # wide bandwidth: stride_B + seq/rand bandwidth columns
        bw_cols = [c for c in low if re.search(r"(seq|sequential).*gbs|rand.*gbs|random.*gbs", c)]
        if ("stride_b" in low) and bw_cols:
            stride = df[lowmap["stride_b"]].astype(int)
            rows=[]
            for c in bw_cols:
                patt = "seq" if "seq" in c else "random"
                vals = df[lowmap[c]].astype(float)
                rows += [{"pattern":patt,"stride_B":int(s),"metric":"bandwidth_GBs","value":float(v),"run_id":1}
                         for s,v in zip(stride, vals)]
            out = pd.DataFrame(rows)
            write_once("ps_written", out, "pattern_stride_all.csv"); continue

    # ----- R/W mix bandwidth
    if not rw_written:
        # rw_mix label + bandwidth
        if "rw_mix" in low and any(k in low for k in ("bandwidth_gbs","gbs","bw_gbs","throughput_gbs")):
            bwc = lowmap.get("bandwidth_gbs") or lowmap.get("gbs") \
                or lowmap.get("bw_gbs") or lowmap.get("throughput_gbs")
            out = df.rename(columns={lowmap["rw_mix"]:"rw_mix", bwc:"bandwidth_GBs"})
            if "run_id" not in out: out["run_id"]=1
            write_once("rw_written", out[["rw_mix","bandwidth_GBs","run_id"]], "rw_mix_all.csv"); continue
        # read%/write% + BW
        if {"read_pct","write_pct","bandwidth_gbs"} <= set(low):
            lab = df[lowmap["read_pct"]].astype(int).astype(str)+"R"+df[lowmap["write_pct"]].astype(int).astype(str)+"W"
            out = pd.DataFrame({"rw_mix":lab, "bandwidth_GBs":df[lowmap["bandwidth_gbs"]].astype(float), "run_id":1})
            write_once("rw_written", out, "rw_mix_all.csv"); continue

    # ----- Intensity curve (threads vs loaded latency & tput)
    if not int_written:
        if "threads" in low:
            latc = lowmap.get("loaded_latency_ns") or lowmap.get("latency_ns") \
                 or lowmap.get("loaded_ns") or lowmap.get("lat_ns")
            thc  = lowmap.get("throughput_gbs") or lowmap.get("tput_gbs") \
                 or lowmap.get("bw_gbs") or lowmap.get("bandwidth_gbs")
            if latc and thc:
                out = df.rename(columns={lowmap["threads"]:"threads", latc:"loaded_latency_ns", thc:"throughput_GBs"})
                if "run_id" not in out: out["run_id"]=1
                write_once("int_written", out[["threads","loaded_latency_ns","throughput_GBs","run_id"]],
                           "intensity_loaded_latency.csv"); continue

    # ----- Working-set sweep (bytes vs ns)
    if not wss_written:
        cand_w = next((lowmap[k] for k in ("working_set_b","wss_b","footprint_b","size_b","bytes") if k in low), None)
        cand_l = next((lowmap[k] for k in ("latency_ns","lat_ns","read_lat_ns") if k in low), None)
        if cand_w and cand_l:
            out = df.rename(columns={cand_w:"working_set_B", cand_l:"latency_ns"})
            if "run_id" not in out: out["run_id"]=1
            write_once("wss_written", out[["working_set_B","latency_ns","run_id"]],
                       "latency_vs_wss.csv"); continue

    # ----- Cache kernel perf (IPC vs MPKI)
    if not cache_written and {"cycles","instructions"} <= set(low) and \
       any(k in low for k in ("llc-load-misses","llc_misses")) and \
       any(k in low for k in ("size_b","size","working_set_b")) and \
       any(k in low for k in ("stride_b","stride")):
        S = lowmap.get("size_b") or lowmap.get("size") or lowmap.get("working_set_b")
        ST= lowmap.get("stride_b") or lowmap.get("stride")
        L = lowmap.get("llc-load-misses") or lowmap.get("llc_misses")
        out = df.rename(columns={S:"size_B", ST:"stride_B", L:"llc_misses",
                                 lowmap["cycles"]:"cycles", lowmap["instructions"]:"instr"})
        if "run_id" not in out: out["run_id"]=1
        write_once("cache_written", out[["size_B","stride_B","run_id","cycles","instr","llc_misses"]],
                   "cache_kernel_perf.csv"); continue

    # ----- TLB perf (IPC vs dTLB MPKI)
    if not tlb_written and {"cycles","instructions"} <= set(low) and \
       any(k in low for k in ("dtlb-load-misses","dtlb_misses")) and \
       any(k in low for k in ("size_b","size")) and \
       any(k in low for k in ("hugepages","thp","hp")):
        S = lowmap.get("size_b") or lowmap.get("size")
        HP= lowmap.get("hugepages") or lowmap.get("thp") or lowmap.get("hp")
        M = lowmap.get("dtlb-load-misses") or lowmap.get("dtlb_misses")
        out = df.rename(columns={S:"size_B", HP:"hugepages", M:"dtlb_load_misses",
                                 lowmap["cycles"]:"cycles", lowmap["instructions"]:"instr"})
        if "run_id" not in out: out["run_id"]=1
        write_once("tlb_written", out[["size_B","hugepages","run_id","cycles","instr","dtlb_load_misses"]],
                   "tlb_kernel_perf.csv"); continue

print("\nsummary:",
      dict(zeroq=zeroq_written, pattern_stride=ps_written, rw_mix=rw_written,
           intensity=int_written, wss=wss_written, cache_perf=cache_written, tlb_perf=tlb_written))
print("canonical outputs ->", OUT)
