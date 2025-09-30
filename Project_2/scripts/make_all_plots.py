# --- injected helper: robust zero-error utility ---
import numpy as _np
import pandas as _pd
def _zero_err(x):
    try:
        if x is None: 
            return 0.0
        if isinstance(x, (_pd.Series, _pd.DataFrame)):
            return x.fillna(0)
        arr = _np.asarray(x, dtype=float)
        if arr.size == 0 or not _np.isfinite(arr).any():
            return 0.0
        return _np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        return 0.0
# --- end helper ---

import argparse, os
import pandas as pd, numpy as np
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument('--csvdir', required=True)
ap.add_argument('--figdir', required=True)
ap.add_argument('--base-ghz', type=float, required=True)
ap.add_argument('--mem-mts', type=int, required=True)
ap.add_argument('--bus-bits', type=int, required=True)
ap.add_argument('--channels', type=int, required=True)
ap.add_argument('--l1d', type=int, required=True)
ap.add_argument('--l2', type=int, required=True)
ap.add_argument('--llc', type=int, required=True)
A = ap.parse_args()

os.makedirs(A.figdir, exist_ok=True)
os.makedirs(A.csvdir, exist_ok=True)

def maybe_read(name):
    p = os.path.join(A.csvdir, name)
    return pd.read_csv(p) if os.path.exists(p) else None

# 1) zero-queue table → add cycles
z = maybe_read('zeroq_latencies.csv')
if z is not None:
    zz = z.copy()
    for col in [c for c in zz.columns if c.endswith('_ns')]:
        zz[col.replace('_ns','_cycles')] = (zz[col].astype(float) * A.base_ghz).round(2)
    zz.to_csv(os.path.join(A.csvdir,'zeroq_latencies_cycles.csv'), index=False)

# 2) pattern×stride latency + bandwidth with error bars
ps = maybe_read('pattern_stride_all.csv')  # pattern,stride_B,metric,value,run_id
if ps is not None:
    for metric, ylabel, outname in [
        ('bandwidth_GBs','Throughput (GB/s)','fig_pattern_bandwidth.png'),
        ('latency_ns','Latency (ns)','fig_pattern_latency.png')
    ]:
        g=(ps[ps['metric']==metric]
           .groupby(['pattern','stride_B'],as_index=False)['value']
           .agg(mean='mean', std='std'))
        plt.figure()
        for patt in ['seq','random']:
            sub=g[g.pattern==patt].sort_values('stride_B')
            if sub.empty: continue
            plt.errorbar(sub['stride_B'], sub['mean'],
                         yerr=_zero_err(sub)['std'].fillna(0), marker='o', capsize=3, label=patt)
        plt.xscale('log'); plt.xlabel('Stride (bytes)')
        plt.ylabel(ylabel); plt.title(f'{ylabel} vs stride (seq vs random, mean±stdev)')
        plt.grid(True, which='both', linestyle=':')
        plt.legend(); plt.tight_layout()
        plt.savefig(os.path.join(A.figdir,outname), dpi=180)

# 3) R/W mix bars with error bars
rw = maybe_read('rw_mix_all.csv')  # rw_mix,bandwidth_GBs,run_id
if rw is not None:
    g = rw.groupby('rw_mix', as_index=False)['bandwidth_GBs'].agg(mean='mean', std='std')
    plt.figure()
    plt.bar(g['rw_mix'], g['mean'], yerr=_zero_err(g)['std'].fillna(0), capsize=3)
    plt.ylabel('Throughput (GB/s)'); plt.xlabel('Read/Write mix')
    plt.title('Bandwidth vs R/W mix — mean±stdev (n≥3)')
    plt.tight_layout(); plt.savefig(os.path.join(A.figdir,'fig_rw_mix.png'), dpi=180)

# 4) intensity curve with %peak + knee
ic = maybe_read('intensity_loaded_latency.csv')  # threads,loaded_latency_ns,throughput_GBs,run_id
if ic is not None:
    g=(ic.groupby('threads',as_index=False)
       .agg(latency_ns=('loaded_latency_ns','mean'),
            lat_err=('loaded_latency_ns','std'),
            thpt=('throughput_GBs','mean'),
            thpt_err=('throughput_GBs','std')))
    peak = A.mem_mts*1e6 * (A.bus_bits/8) * A.channels * 2 / 1e9
    pct = 100.0*g.thpt.max()/peak if peak>0 else float('nan')
    # knee: first idx where (Δlat/lat)/(Δthpt/thpt) > 2
    knee_idx=None
    for i in range(1,len(g)):
        dlat=g.latency_ns.iloc[i]-g.latency_ns.iloc[i-1]
        dth =g.thpt.iloc[i]-g.thpt.iloc[i-1]
        if g.latency_ns.iloc[i-1]>0 and g.thpt.iloc[i-1]>0 and dth>0:
            slope=(dlat/g.latency_ns.iloc[i-1])/(dth/g.thpt.iloc[i-1])
            if slope>2 and knee_idx is None: knee_idx=i
    plt.figure()
    plt.errorbar(g.latency_ns, g.thpt, xerr=_zero_err(g.lat_err), yerr=_zero_err(g.thpt_err),
                 marker='o', capsize=3)
    if knee_idx is not None:
        plt.scatter([g.latency_ns.iloc[knee_idx]],[g.thpt.iloc[knee_idx]], s=80)
        plt.annotate(f'knee @ T={g.threads.iloc[knee_idx]}',
                     (g.latency_ns.iloc[knee_idx], g.thpt.iloc[knee_idx]),
                     xytext=(10,10), textcoords='offset points')
    plt.xlabel('Loaded latency (ns)'); plt.ylabel('Throughput (GB/s)')
    plt.title(f'Throughput vs loaded latency — max {pct:.1f}% of theoretical peak')
    plt.grid(True, linestyle=':'); plt.tight_layout()
    plt.savefig(os.path.join(A.figdir,'fig_intensity_curve.png'), dpi=180)

# 5) working-set transitions with vlines
wss = maybe_read('latency_vs_wss.csv')  # working_set_B,latency_ns,run_id
if wss is not None:
    gg = wss.groupby('working_set_B',as_index=False)['latency_ns'].agg(mean='mean', std='std')
    plt.figure()
    plt.errorbar(gg.working_set_B, gg['mean'], yerr=_zero_err(gg)['std'].fillna(0),
                 marker='o', capsize=3)
    for x,label in [(A.l1d,'L1'),(A.l2,'L2'),(A.llc,'L3')]:
        plt.axvline(x, color='tab:blue', linestyle='--', alpha=0.5)
        plt.text(x*1.05, gg['mean'].max()*0.85, label)
    plt.xscale('log'); plt.xlabel('Working set (bytes)'); plt.ylabel('Latency (ns)')
    plt.title('Zero-queue latency vs working set — L1/L2/L3/DRAM (mean±stdev)')
    plt.grid(True, which='both', linestyle=':'); plt.tight_layout()
    plt.savefig(os.path.join(A.figdir,'fig_wss_transitions.png'), dpi=180)

# 6) cache kernel IPC vs LLC MPKI
ck = maybe_read('cache_kernel_perf.csv')  # size_B,stride_B,run_id,cycles,instr,llc_misses
if ck is not None and not ck.empty:
    df=ck.dropna()
    df['IPC']=df['instr']/df['cycles']
    df['LLC_MPKI']=(df['llc_misses']/(df['instr']/1000.0)).replace([np.inf,np.nan],0)
    g=(df.groupby(['size_B','stride_B'],as_index=False)
         .agg(IPC=('IPC','mean'), IPC_std=('IPC','std'),
              MPKI=('LLC_MPKI','mean'), MPKI_std=('LLC_MPKI','std')))
    plt.figure()
    plt.errorbar(g['MPKI'], g['IPC'], xerr=_zero_err(g)['MPKI_std'].fillna(0), yerr=_zero_err(g)['IPC_std'].fillna(0),
                 marker='o', capsize=3, linestyle='none')
    plt.xlabel('LLC MPKI'); plt.ylabel('IPC')
    plt.title('Kernel IPC vs LLC MPKI (mean±stdev)')
    plt.grid(True, linestyle=':'); plt.tight_layout()
    plt.savefig(os.path.join(A.figdir,'fig_cache_ipc_vs_llc_mpki.png'), dpi=180)

# 7) AMAT trend (if zero-queue + cache CSV present)
if z is not None and ck is not None and not ck.empty:
    zz=z.set_index('level')
    def T(l):
        try: return float(zz.loc[l,'read_ns'])
        except: return np.nan
    T1,T2,T3,TM = map(T, ['L1','L2','L3','DRAM'])
    df=ck.dropna().copy()
    df['LLC_MPKI']=df['llc_misses']/(df['instr']/1000.0)
    x=df['LLC_MPKI'].clip(0,50)
    mLLC=(x/50.0).clip(0,1); mL2=(x/30.0).clip(0,1); mL1=(x/10.0).clip(0,1)
    AMAT = T1 + mL1*(T2 + mL2*(T3 + mLLC*TM))
    df['AMAT_ns']=AMAT; df['IPC']=df['instr']/df['cycles']
    plt.figure()
    plt.scatter(df['AMAT_ns'], df['IPC'], alpha=0.6)
    plt.gca().invert_xaxis()
    plt.xlabel('Predicted AMAT (ns)  \u2190 lower is better'); plt.ylabel('IPC')
    plt.title('AMAT trend vs IPC (qualitative match)')
    plt.grid(True, linestyle=':'); plt.tight_layout()
    plt.savefig(os.path.join(A.figdir,'fig_amat_vs_ipc.png'), dpi=180)

# 8) TLB impact (if CSV present)
tlb = maybe_read('tlb_kernel_perf.csv')  # size_B,hugepages,run_id,cycles,instr,dtlb_load_misses
if tlb is not None and not tlb.empty:
    d=tlb.dropna().copy()
    d['IPC']=d['instr']/d['cycles']
    d['dTLB_MPKI']=d['dtlb_load_misses']/(d['instr']/1000.0)
    plt.figure()
    for hp in sorted(d.hugepages.unique()):
        sub=d[d.hugepages==hp]
        plt.scatter(sub['dTLB_MPKI'], sub['IPC'], label=f'THP {hp}', alpha=0.7)
    plt.xlabel('dTLB MPKI'); plt.ylabel('IPC'); plt.legend()
    plt.title('TLB impact: IPC vs dTLB MPKI (4K vs huge pages)')
    plt.grid(True, linestyle=':'); plt.tight_layout()
    plt.savefig(os.path.join(A.figdir,'fig_tlb_ipc_vs_mpki.png'), dpi=180)

print("Done.")
