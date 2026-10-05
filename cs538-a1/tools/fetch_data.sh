#!/usr/bin/env bash
# Download the Route Views LINX data used in CS538 A1 Part 2.
# RIBs are dumped every 2 hours; update files cover 15 minutes each.
set -euo pipefail
cd "$(dirname "$0")/../data"
BASE=https://archive.routeviews.org/route-views.linx/bgpdata

get() { [ -s "$(basename "$1")" ] || curl -fSLO --retry 3 "$BASE/$1"; }

# 2.2 Level 3 leak: before (14:00) and after (18:00) on 2017-11-06
get 2017.11/RIBS/rib.20171106.1400.bz2
get 2017.11/RIBS/rib.20171106.1800.bz2

# 2.3 Egypt: last RIB before the shutdown (19:19), plus every update file
# covering 21:00-23:00. In 2011 LINX file times were not on round minutes.
get 2011.01/RIBS/rib.20110127.1919.bz2
for t in 2050 2105 2122 2137 2152 2207 2222 2237 2252; do
  get 2011.01/UPDATES/updates.20110127.$t.bz2
done
ls -lh
