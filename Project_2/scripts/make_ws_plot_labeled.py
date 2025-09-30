import os, numpy as np, pandas as pd, matplotlib.pyplot as plt

os.makedirs("plots", exist_ok=True)
os.makedirs("results/lat", exist_ok=True)

latp = "results/lat/latency_ws.csv"
df = pd.read_csv(latp)
need = {'bytes','lat_ns_est'}
assert need.issubset(df.columns), f"{latp} missing columns {need - set(df.columns)}"

# Aggregate by working-set size
g = df.groupby('bytes')['lat_ns_est'].agg(['mean','std','count']).reset_index().sort_values('bytes')

# Your machine's cache sizes (bytes)
L1_BYTES = 48 * 1024
L2_BYTES = 1250 * 1024     # 1.25 MiB
L3_BYTES = 8 * 1024 * 1024

levels = [
    ('L1',  L1_BYTES),
    ('L2',  L2_BYTES),
    ('L3',  L3_BYTES),
]

# Find the closest measured point to each level size
rows = []
for name, target in levels:
    i = int((g['bytes'] - target).abs().idxmin())
    bi = int(g.loc[i,'bytes'])
    mean_ns = float(g.loc[i,'mean'])
    std_ns  = float(g.loc[i,'std'])
    rows.append({'level': name, 'target_bytes': int(target), 'closest_bytes': bi,
                 'latency_ns_mean': mean_ns, 'latency_ns_std': std_ns})

# DRAM: use the largest measured point as the DRAM representative
bi = int(g['bytes'].iloc[-1])
mean_ns = float(g['mean'].iloc[-1])
std_ns  = float(g['std'].iloc[-1])
rows.append({'level': 'DRAM', 'target_bytes': int(max(L3_BYTES*2, bi)), 'closest_bytes': bi,
             'latency_ns_mean': mean_ns, 'latency_ns_std': std_ns})

tab = pd.DataFrame(rows)

# Add cycles if CPU_HZ is provided (e.g., CPU_HZ=4.2e9)
HZ = os.environ.get('CPU_HZ')
if HZ:
    hz = float(HZ)
    tab['latency_cycles_mean'] = tab['latency_ns_mean'] * 1e-9 * hz
    tab['latency_cycles_std']  = tab['latency_ns_std']  * 1e-9 * hz

tab.to_csv("results/lat/latency_levels_table.csv", index=False)

# ---- PLOT ----
plt.figure()
plt.errorbar(g['bytes'], g['mean'], yerr=g['std'], marker='o', linewidth=1)

# Vertical lines at your cache sizes
for name, x in levels:
    plt.axvline(x, ls='--', alpha=0.6)
    # annotate near the mean latency at closest point
    i = int((g['bytes'] - x).abs().idxmin())
    y = g.loc[i,'mean']
    label = f"{name} (~{x//1024}KB)" if x < (1<<20) else f"{name} (~{x//(1<<20)}MB)"
    plt.annotate(label, xy=(x, y), xytext=(10, 10), textcoords='offset points',
                 bbox=dict(boxstyle="round,pad=0.2", fc="w", ec="0.5", alpha=0.8))

# DRAM region label (to the right of L3)
x_dram = max(L3_BYTES * 2, g['bytes'].iloc[-1])
y_dram = g['mean'].iloc[-1]
plt.annotate("DRAM", xy=(x_dram, y_dram), xytext=(-30, -25), textcoords='offset points',
             bbox=dict(boxstyle="round,pad=0.2", fc="w", ec="0.5", alpha=0.8))

plt.xscale('log')
plt.xlabel('Working set (bytes)')
plt.ylabel('Latency (ns)')
plt.title('Zero-queue latency vs working set — L1 / L2 / L3 / DRAM (labeled)')
plt.grid(True, which='both')
plt.tight_layout()
plt.savefig("plots/latency_vs_ws_labeled.png", dpi=180)

print("Wrote plots/latency_vs_ws_labeled.png and results/lat/latency_levels_table.csv")
