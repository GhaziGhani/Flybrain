#!/usr/bin/env python3
"""Plot cumulative Egyptian prefix withdrawals from egypt_parse output.

Usage: python3 plot_withdrawals.py ../results/egypt_withdrawals.dat ../results/egypt_withdrawals.png
"""
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

src, out = sys.argv[1], sys.argv[2]
ts, total = [], []
with open(src) as fh:
    for line in fh:
        t, n = line.split()
        ts.append(datetime.fromtimestamp(int(t), tz=timezone.utc))
        total.append(int(n))

fig, ax = plt.subplots(figsize=(9, 5))
ax.step(ts, total, where="post", color="#1f5fa8", linewidth=1.8)
ax.set_xlabel("Time (UTC), 27 January 2011")
ax.set_ylabel("Cumulative Egyptian prefix withdrawals")
ax.set_title("Egyptian prefix withdrawals seen at Route Views LINX")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(out, dpi=150)
print(f"wrote {out}: {len(total)} withdrawals, {ts[0]:%H:%M:%S} -> {ts[-1]:%H:%M:%S} UTC")
