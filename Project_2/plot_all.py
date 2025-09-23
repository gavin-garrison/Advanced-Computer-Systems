import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("plots", exist_ok=True)

def read_csv_safe(p):
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

def mean_std(df, key, val):
    g = df.groupby(key)[val].agg(['mean','std']).reset_index()
    return g

# -------- 1) Zero-queue latency vs working set --------
lat = read_csv_safe("results/lat/latency_ws.csv")
if not lat.empty and {'bytes','lat_ns_est'}.issubset(lat.columns):
    g = mean_std(lat, 'bytes', 'lat_ns_est')
    plt.figure()
    plt.errorbar(g['bytes'], g['mean'], yerr=g['std'], marker='o')
    plt.xscale('log'); plt.xlabel('Working set (bytes)'); plt.ylabel('Latency (ns)')
    plt.title('Zero-queue latency vs working set'); plt.grid(True, which='both')
    # optional cache-size guides; tweak for your CPU if you want
    for cap in [32*1024, 256*1024, 20*1024*1024]:
        plt.axvline(cap, ls='--', alpha=0.4)
    plt.tight_layout(); plt.savefig('plots/latency_vs_ws.png', dpi=180)

# -------- 2) Pattern × stride (seq/random × 64/256/1024B; 100%R) --------
frames=[]
for S in [64,256,1024]:
    for pat in ['seq','random']:
        f=f"results/bw/bw_{pat}_{S}_100R.csv"
        d=read_csv_safe(f)
        if not d.empty:
            d['label']=f"{pat}-{S}B"
            frames.append(d)
bw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
if not bw.empty:
    xcol = 'stride_B' if 'stride_B' in bw.columns else 'stride'
    if {'GBps', xcol}.issubset(bw.columns):
        plt.figure()
        for lbl, sub in bw.groupby('label'):
            g = mean_std(sub, xcol, 'GBps')
            plt.plot(g[xcol], g['mean'], marker='o', label=lbl)
        plt.xscale('log'); plt.xlabel('Stride (bytes)'); plt.ylabel('Throughput (GB/s)')
        plt.title('Bandwidth vs stride (seq vs random, 100% reads)')
        plt.legend(); plt.grid(True, which='both'); plt.tight_layout()
        plt.savefig('plots/bw_stride_matrix.png', dpi=180)

# -------- 3) Read/Write mix @64B stride --------
mix_frames=[]
for mix in ['100R','100W','70R30W','50R50W']:
    d=read_csv_safe(f"results/bw/mix_{mix}.csv")
    if not d.empty:
        d['mix']=mix
        mix_frames.append(d)
mixdf = pd.concat(mix_frames, ignore_index=True) if mix_frames else pd.DataFrame()
if not mixdf.empty and 'GBps' in mixdf.columns:
    plt.figure()
    order=['100R','100W','70R30W','50R50W']
    means=[mixdf[mixdf['mix']==m]['GBps'].mean() if (mixdf['mix']==m).any() else np.nan for m in order]
    plt.bar(order, means)
    plt.xlabel('Read/Write mix'); plt.ylabel('Throughput (GB/s)')
    plt.title('Bandwidth vs R/W mix (stride 64B, 1 thread)')
    plt.grid(axis='y'); plt.tight_layout(); plt.savefig('plots/bw_rw_mix.png', dpi=180)

# -------- 4) Intensity sweep: throughput vs threads --------
ints=[]
for f in sorted(glob.glob("results/bw/intensity_T*.csv")):
    d=read_csv_safe(f)
    if not d.empty: ints.append(d)
ints = pd.concat(ints, ignore_index=True) if ints else pd.DataFrame()
if not ints.empty and {'threads','GBps'}.issubset(ints.columns):
    g = mean_std(ints, 'threads', 'GBps')
    plt.figure()
    plt.plot(g['threads'], g['mean'], marker='o')
    plt.xlabel('Threads'); plt.ylabel('Throughput (GB/s)')
    plt.title('Intensity sweep (throughput vs threads)')
    plt.grid(True); plt.tight_layout(); plt.savefig('plots/intensity_threads.png', dpi=180)

# -------- 5) perf (WSL-friendly): cache miss % and dTLB MPKI --------
def parse_perf_csv(path):
    if not os.path.exists(path): return None
    rows=[]
    with open(path) as f:
        for line in f:
            parts=line.strip().split(',')
            if len(parts) < 4: 
                continue
            # format: value,unit,?,event
            try:
                val=float(parts[0]); event=parts[3]
                rows.append((event,val))
            except:
                pass
    return dict(rows)

cases = {
    'local': 'results/perf/saxpy_local.perf.csv',
    'random': 'results/perf/saxpy_random.perf.csv',
    'tlb_span16': 'results/perf/saxpy_tlb_span16.perf.csv',
    'tlb_span16_huge': 'results/perf/saxpy_tlb_span16_huge.perf.csv',
}
perf_data = {k: parse_perf_csv(v) for k,v in cases.items() if os.path.exists(v)}
if perf_data:
    def ratio(d, num, den):
        if not d: return np.nan
        n = d.get(num, np.nan); de = d.get(den, np.nan)
        return (n/de*100.0) if np.isfinite(n) and np.isfinite(de) and de>0 else np.nan
    def mpki(d, num):
        if not d: return np.nan
        n = d.get(num, np.nan); inst = d.get('instructions', np.nan)
        return (n/(inst/1e3)) if np.isfinite(n) and np.isfinite(inst) and inst>0 else np.nan

    rows=[]
    for name,d in perf_data.items():
        rows.append({
            'case': name,
            'cache_miss_%': ratio(d,'cache-misses','cache-references'),
            'dtlb_mpki':    mpki(d,'dTLB-load-misses'),
        })
    perfd = pd.DataFrame(rows).fillna(0)
    perfd.to_csv('results/perf/summary_wsl.csv', index=False)

    fig, ax1 = plt.subplots()
    idx = np.arange(len(perfd))
    ax1.bar(idx-0.2, perfd['cache_miss_%'], width=0.4, label='cache miss %')
    ax1.set_ylabel('Cache miss (%)')
    ax1.set_xticks(idx, perfd['case'], rotation=15)
    ax2 = ax1.twinx()
    ax2.plot(idx+0.2, perfd['dtlb_mpki'], marker='o', label='dTLB MPKI')
    ax2.set_ylabel('dTLB MPKI')
    ax1.set_title('perf: cache miss % (bars) and dTLB MPKI (line)')
    h1,l1=ax1.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels()
    ax1.legend(h1+h2, l1+l2, loc='best')
    fig.tight_layout(); fig.savefig('plots/perf_cache_tlb_wsl.png', dpi=180)

    # ---- Intensity: throughput vs latency (knee) ----
ints = pd.concat([pd.read_csv(p) for p in sorted(glob.glob("results/bw/intensity_T*.csv"))], ignore_index=True) \
        if glob.glob("results/bw/intensity_T*.csv") else pd.DataFrame()
if not ints.empty and {'GBps','lat_est_ns','threads'}.issubset(ints.columns):
    g = ints.groupby('threads')[['GBps','lat_est_ns']].mean().reset_index()
    # single curve: x = latency, y = throughput
    plt.figure()
    plt.plot(g['lat_est_ns'], g['GBps'], marker='o')
    # mark knee: simple heuristic = point with max curvature in (lat, gbps)
    if len(g) >= 3:
      x, y = g['lat_est_ns'].to_numpy(), g['GBps'].to_numpy()
      # discrete curvature proxy
      kappa = []
      for i in range(1,len(x)-1):
          dx1, dy1 = x[i]-x[i-1], y[i]-y[i-1]
          dx2, dy2 = x[i+1]-x[i], y[i+1]-y[i]
          cross = abs(dx1*dy2 - dy1*dx2)
          norm  = (dx1*dx1+dy1*dy1)**0.5 * (dx2*dx2+dy2*dy2)**0.5
          kappa.append(cross/(norm+1e-12))
      knee_i = 1 + int(np.argmax(kappa))
      plt.scatter([x[knee_i]],[y[knee_i]], s=80)
      plt.annotate(f'knee @ T={int(g.loc[knee_i,"threads"])}',
                   (x[knee_i],y[knee_i]), xytext=(10,10), textcoords='offset points')
    plt.xlabel('Loaded latency (ns)'); plt.ylabel('Throughput (GB/s)')
    plt.title('Throughput vs latency (intensity sweep)')
    plt.grid(True); plt.tight_layout(); plt.savefig('plots/intensity_knee.png', dpi=180)


# -------- 6) Runtime-only view for cache/TLB impact (always works) --------
def runt_plot():
    cases = [
        ("local",  "results/kernel/saxpy_local.csv"),
        ("random", "results/kernel/saxpy_random.csv"),
        ("tlb_span16", "results/kernel/saxpy_tlb_span16.csv"),
        ("tlb_span16_huge", "results/kernel/saxpy_tlb_span16_huge.csv"),
    ]
    rows=[]
    for name, p in cases:
        df = read_csv_safe(p)
        if not df.empty and 'sec' in df.columns:
            rows.append((name, df['sec'].mean()))
    if rows:
        df = pd.DataFrame(rows, columns=['case','sec'])
        plt.figure()
        plt.bar(df['case'], df['sec'])
        plt.ylabel('Runtime (s)'); plt.title('SAXPY runtime by case (cache/TLB impact)')
        plt.grid(axis='y'); plt.tight_layout(); plt.savefig('plots/kernel_runtime.png', dpi=180)
# ---- Latency table with cycles (export CSV) ----
lat = read_csv_safe("results/lat/latency_ws.csv")
if not lat.empty and {'bytes','lat_ns_est'}.issubset(lat.columns):
    g = mean_std(lat, 'bytes', 'lat_ns_est')
    # allow CPU_HZ env to convert to cycles; else assume 3.5 GHz
    HZ = float(os.environ.get('CPU_HZ', '3.5e9'))
    g['cycles_mean'] = g['mean'] * 1e-9 * HZ
    g['cycles_std']  = g['std']  * 1e-9 * HZ
    g.rename(columns={'bytes':'working_set_bytes','mean':'latency_ns_mean','std':'latency_ns_std'}, inplace=True)
    g.to_csv('results/lat/latency_table.csv', index=False)


runt_plot()
print("Saved plots to plots/.")
