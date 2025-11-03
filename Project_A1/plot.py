import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

out = Path(__file__).resolve().parent / "results"
out.mkdir(exist_ok=True, parents=True)

# 1) Affinity plot
try:
    df = pd.read_csv(out / "affinity.csv")
    # extract time
    df['pinned'] = df['cpu'].apply(lambda x: 'pinned' if int(x)>=0 else 'not_pinned')
    ax = df.boxplot(column='time_s', by='pinned')
    plt.title('Compute jitter: pinned vs not pinned')
    plt.suptitle('')
    plt.xlabel('')
    plt.ylabel('time (s) for fixed iters')
    plt.savefig(out / "affinity_box.png", bbox_inches='tight')
    plt.close()
except Exception as e:
    print("affinity plot error:", e)

# 2) THP throughput
try:
    df = pd.read_csv(out / "thp.csv")
    df['label'] = df['thp_flag'].map({1:'THP on',0:'THP off'})
    ax = df.plot(x='label', y='GBps', kind='bar')
    plt.title('Memcpy throughput: THP on vs off')
    plt.ylabel('GB/s')
    plt.xlabel('')
    plt.savefig(out / "thp_bar.png", bbox_inches='tight')
    plt.close()
except Exception as e:
    print("thp plot error:", e)

# 3) Stride sensitivity
try:
    df = pd.read_csv(out / "stride.csv")
    ax = df.plot(x='strideB', y='ns_per_access', marker='o')
    plt.title('Prefetcher/cache: ns per access vs stride')
    plt.xlabel('stride (bytes)')
    plt.ylabel('ns/access')
    plt.grid(True)
    plt.savefig(out / "stride_line.png", bbox_inches='tight')
    plt.close()
except Exception as e:
    print("stride plot error:", e)

# 4) SMT total time (single point) - nothing to plot unless multiple runs, so just echo path
print("Generated plots (where applicable) into:", out)
