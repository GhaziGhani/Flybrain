#!/usr/bin/env python3
"""Count distinct AS paths to Netflix's 198.45.49.0/24 in a `bgpdump -m` RIB dump.

Usage: bgpdump -m rib.bz2 | python3 netflix_paths.py [prefix]
"""
import sys
from collections import Counter

prefix = sys.argv[1] if len(sys.argv) > 1 else "198.45.49.0/24"
paths = Counter()
peers = Counter()
for line in sys.stdin:
    f = line.rstrip("\n").split("|")
    if len(f) > 6 and f[0].startswith("TABLE_DUMP") and f[5] == prefix:
        paths[f[6]] += 1
        peers[f[6]] = peers[f[6]] or f[3] + " AS" + f[4]

print(f"prefix {prefix}: {sum(paths.values())} RIB entries, {len(paths)} distinct AS paths")
for path, n in sorted(paths.items(), key=lambda kv: (len(kv[0].split()), kv[0])):
    hops = path.split()
    via3356 = "  <-- via AS3356" if "3356" in hops else ""
    print(f"  len={len(hops):2d}  x{n}  {path}{via3356}")
