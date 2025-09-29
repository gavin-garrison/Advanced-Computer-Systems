#!/usr/bin/env python3
import json, glob, re, math, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

OUT = "out"
os.makedirs(OUT, exist_ok=True)

def sec_key(j):
    # fio sometimes nests stats under 'read'/'write' or 'trim'; pick whichever exists
    for k in ("read","write","randread","randwrite"):
        if k in j: return k
    # fallback: jobs[0] may already be the dict of metrics
    return None

def metrics_from_job(j):
    bw_bytes = j.get("bw_bytes")
    MBps = (bw_bytes/1048576.0) if bw_bytes is not None else j.get("bw",0)/1024.0
    IOPS = j.get("iops",0.0)
    lat = j.get("clat_ns") or j.get("lat_ns") or {}
    mean = lat.get("mean", float("nan"))/1e6
    pct  = lat.get("percentile") or lat.get("percentiles") or {}
    p95  = (pct.get("95.000000") if "95.000000" in pct else float("nan"))/1e6
    p99  = (pct.get("99.000000") if "99.000000" in pct else float("nan"))/1e6
    return dict(MBps=MBps, IOPS=IOPS, lat_ms=mean, p95_ms=p95, p99_ms=p99)

def read_json(path):
    d = json.load(open(path))
    j0 = d["jobs"][0]
    k  = sec_key(j0)
    j  = j0[k] if k else j0
    m  = metrics_from_job(j)
    m["path"] = path
    return m

# ---------- 1) Zero-queue table ----------
zfiles = [
    f"{OUT}/zero_4k_randread.json",
    f"{OUT}/zero_4k_randwrite.json",
    f"{OUT}/zero_128k_seqread.json",
    f"{OUT}/zero_128k_seqwrite.json",
]
rows=[]
for p in zfiles:
    r = read_json(p)
    if "rand" in p and "read" in p: pat, bs, op = "random","4k","read"
    if "rand" in p and "write" in p: pat, bs, op = "random","4k","write"
    if "seqread" in p: pat, bs, op = "sequential","128k","read"
    if "seqwrite" in p: pat, bs, op = "sequential","128k","write"
    rows.append(dict(Pattern=pat, Block=bs, Op=op, IOPS=r["IOPS"], **{"MB/s":r["MBps"]},
                    **{"Avg (ms)":r["lat_ms"], "p95 (ms)":r["p95_ms"], "p99 (ms)":r["p99_ms"]}))
zero_df = pd.DataFrame(rows)
zero_df.to_csv(f"{OUT}/zero_queue_pretty.csv", index=False)

# ---------- 2) Block-size sweeps ----------
def collect_bs(kind):  # kind in {"rand","seq"}
    rec=[]
    for p in glob.glob(f"{OUT}/bs_{kind}_*_*.json"):
        m = re.search(rf"{OUT}/bs_{kind}_(R|W)_(\d+k)_(\d+)\.json", p)
        if not m: continue
        op, bs, rep = m.groups()
        r = read_json(p)
        rec.append(dict(pattern=kind, op=op, bs=bs, rep=int(rep), **r))
    df = pd.DataFrame(rec)
    df["bs_order"] = df["bs"].str.replace("k","",regex=False).astype(int)
    df = df.sort_values(["op","bs_order","rep"])
    return df

def plot_bs(df, label_prefix):
    g = df.groupby(["op","bs"]).agg(MBps=("MBps","mean"), IOPS=("IOPS","mean"),
                                    lat_ms=("lat_ms","mean"),
                                    MBps_std=("MBps","std"), lat_std=("lat_ms","std")).reset_index()
    # IOPS & MB/s
    ops = {"R":"Read","W":"Write"}
    for metric, fname in [("IOPS", f"{OUT}/bs_sweep_{label_prefix}.png")]:
        fig, axes = plt.subplots(1,2, figsize=(12,4))
        for ax, op in zip(axes, ["R","W"]):
            sub = g[g["op"]==op]
            ax.plot(sub["bs"], sub["IOPS"], marker="o", label=f"{ops[op]} IOPS")
            ax.set_title(f"IOPS vs Block Size ({label_prefix})")
            ax.set_xlabel("Block size"); ax.set_ylabel("IOPS")
        fig.tight_layout(); fig.savefig(fname, dpi=200); plt.close(fig)

    # MB/s (separate figure)
    fig, axes = plt.subplots(1,2, figsize=(12,4))
    for ax, op in zip(axes, ["R","W"]):
        sub = g[g["op"]==op]
        ax.plot(sub["bs"], sub["MBps"], marker="o", label=f"{ops[op]} MB/s")
        ax.set_title(f"Throughput vs Block Size ({label_prefix})")
        ax.set_xlabel("Block size"); ax.set_ylabel("MB/s")
    fig.tight_layout(); fig.savefig(f"{OUT}/bs_sweep_{label_prefix}.png", dpi=200); plt.close(fig)

    # latency with error bars
    fig, ax = plt.subplots(figsize=(9,6))
    for op in ["R","W"]:
        sub = g[g["op"]==op]
        ax.errorbar(sub["bs"], sub["lat_ms"], yerr=sub["lat_std"], marker="o", label=("Read" if op=="R" else "Write"))
    ax.set_title(f"Latency vs Block Size ({label_prefix})")
    ax.set_xlabel("Block size"); ax.set_ylabel("Avg latency (ms)"); ax.legend()
    fig.tight_layout(); fig.savefig(f"{OUT}/bs_sweep_{label_prefix}_latency.png", dpi=200); plt.close(fig)

rand_df = collect_bs("rand");  plot_bs(rand_df, "rand")
seq_df  = collect_bs("seq");   plot_bs(seq_df,  "seq")

# ---------- 3) Read/Write mix ----------
mix_rows=[]
for p in glob.glob(f"{OUT}/mix_*.json"):
    r = read_json(p)
    label = re.search(rf"{OUT}/mix_(.+?)_1\.json", p).group(1)
    mix_rows.append(dict(label=label, IOPS=r["IOPS"], MBps=r["MBps"], latavg_ms=r["lat_ms"]))
mix = pd.DataFrame(mix_rows)
fig, axes = plt.subplots(1,2, figsize=(12,5))
axes[0].bar(mix["label"], mix["IOPS"]); axes[0].set_title("Throughput vs R/W mix (4k rand, QD32)"); axes[0].set_ylabel("IOPS")
axes[1].bar(mix["label"], mix["latavg_ms"]); axes[1].set_title("Avg Latency"); axes[1].set_ylabel("ms")
fig.tight_layout(); fig.savefig(f"{OUT}/rw_mix.png", dpi=200); plt.close(fig)

# ---------- 4) QD trade-off with error bars ----------
def collect_qd(prefix):
    rows=[]
    for p in glob.glob(f"{OUT}/{prefix}_*.json"):
        m = re.search(rf"{OUT}/{re.escape(prefix)}_(\d+)_(\d+)\.json", p)
        if not m: continue
        qd, rep = map(int, m.groups())
        r = read_json(p); rows.append(dict(qd=qd, rep=rep, **r))
    df = pd.DataFrame(rows)
    return df.groupby("qd").agg(MBps=("MBps","mean"), MBps_std=("MBps","std"),
                                IOPS=("IOPS","mean"),  IOPS_std=("IOPS","std"),
                                lat_ms=("lat_ms","mean"), lat_std=("lat_ms","std")).reset_index()

def tradeoff_scatter(df, ycol, title, fname):
    fig, ax = plt.subplots(figsize=(9,6))
    ax.errorbar(df["lat_ms"], df[ycol], xerr=df["lat_std"], yerr=df[f"{ycol}_std"], marker="o")
    ax.set_title(title); ax.set_xlabel("Avg latency (ms)"); ax.set_ylabel("IOPS" if ycol=="IOPS" else "MB/s")
    # knee ~ lowest latency before flattening; annotate QD≈1 visually
    i0 = df["qd"].idxmin()
    ax.annotate("knee ~ QD1", (df.loc[i0,"lat_ms"], df.loc[i0,ycol]), xytext=(df.loc[i0,"lat_ms"]+0.001, df.loc[i0,ycol]+(50 if ycol=="IOPS" else 2)), arrowprops=dict(arrowstyle="->"))
    fig.tight_layout(); fig.savefig(fname, dpi=200); plt.close(fig)

qd4k  = collect_qd("qd_4k_rand");     qd4k["qd"]=qd4k["qd"]
qd128 = collect_qd("qd_128k_seq");    qd128["qd"]=qd128["qd"]
tradeoff_scatter(qd4k,  "IOPS", "Throughput vs Latency (4k rand)",   f"{OUT}/qd_tradeoff_4k_rand_err.png")
tradeoff_scatter(qd128, "MBps", "Throughput vs Latency (128k seq)", f"{OUT}/qd_tradeoff_128k_seq_err.png")

# ---------- 5) Tail latency ----------
def p_from_json(p):
    d=json.load(open(p))["jobs"][0]
    k=sec_key(d); j=d[k] if k else d
    pct=(j.get("clat_ns") or j.get("lat_ns") or {}).get("percentile",{})
    def g(key): 
        v=pct.get(key); 
        return float("nan") if v is None else v/1e6
    return dict(p50=g("50.000000"), p95=g("95.000000"), p99=g("99.000000"), p999=g("99.900000"))

tail=[]
for qd in (8,64):
    path=f"{OUT}/tail_4k_rand_qd{qd}_1.json"
    if os.path.exists(path):
        r=p_from_json(path); r["qd"]=qd; tail.append(r)
if tail:
    tdf=pd.DataFrame(tail).sort_values("qd")
    fig, ax=plt.subplots(figsize=(9,5))
    for c in ["p50","p95","p99","p999"]:
        ax.plot(tdf["qd"], tdf[c], marker="o", label=c)
    ax.set_title("Tail Latency (4k rand)"); ax.set_xlabel("Queue depth"); ax.set_ylabel("Latency (ms)"); ax.legend()
    fig.tight_layout(); fig.savefig(f"{OUT}/tail_latency.png", dpi=200); plt.close(fig)

# ---------- 6) Working-set effect ----------
def label_from_ws(p):
    return "256MiB window" if "ws_small" in p else "8GiB window"
ws=[]
for p in [f"{OUT}/ws_small.json", f"{OUT}/ws_large.json"]:
    if os.path.exists(p):
        r=read_json(p); ws.append(dict(label=label_from_ws(p), MBps=r["MBps"], lat_ms=r["lat_ms"]))
if ws:
    wdf=pd.DataFrame(ws)
    fig, ax1=plt.subplots(figsize=(9,5))
    ax1.bar(wdf["label"], wdf["MBps"], alpha=0.6)
    ax1.set_ylabel("MB/s"); ax1.set_title("Working-set size effect (4k rand, QD32)")
    ax2=ax1.twinx(); ax2.plot(wdf["label"], wdf["lat_ms"], marker="o", color="tab:blue"); ax2.set_ylabel("Latency (ms)")
    fig.tight_layout(); fig.savefig(f"{OUT}/working_set.png", dpi=200); plt.close(fig)

# ---------- 7) Burst→steady bandwidth plot ----------
logs=sorted(glob.glob(f"{OUT}/slc_bw_bw*.log"))
if logs:
    p=logs[0]
    # fio bw log has 5 columns: ms,kbps,iops,bs,zr (we need 2)
    df=pd.read_csv(p, header=None, names=["ms","kbps","iops","bs","zr"])
    df["sec"]=df["ms"]/1000.0; df["MBps"]=df["kbps"]/1024.0
    fig,ax=plt.subplots(figsize=(12,5))
    ax.plot(df["sec"], df["MBps"], alpha=0.25, label="raw")
    # median filter over 5s
    w=10  # 0.5s buckets -> 10≈5s window
    ax.plot(df["sec"], df["MBps"].rolling(w, center=True).median(), label="median(5s)")
    ax.set_xlabel("Time (s)"); ax.set_ylabel("MB/s"); ax.set_title("Write bandwidth over time (128k, QD32, buffered)")
    ax.legend(); fig.tight_layout(); fig.savefig(f"{OUT}/slc_bw.png", dpi=200); plt.close(fig)

# ---------- 8) Compressibility ----------
if all(os.path.exists(f"{OUT}/{x}.json") for x in ["comp0","comp50"]):
    c0=read_json(f"{OUT}/comp0.json")["MBps"]; c5=read_json(f"{OUT}/comp50.json")["MBps"]
    fig,ax=plt.subplots(figsize=(9,5))
    ax.bar(["0% (incompressible)","50%"], [c0,c5])
    ax.set_ylabel("MB/s"); ax.set_title("Effect of payload compressibility (4k rand, QD32)")
    fig.tight_layout(); fig.savefig(f"{OUT}/compressibility.png", dpi=200); plt.close(fig)

print("[ok] Wrote figures and CSVs to out/")
