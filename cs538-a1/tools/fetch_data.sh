#!/usr/bin/env bash
# Download the Route Views LINX data used in CS538 A1 Part 2.
# RIBs are dumped every 2 hours; update files cover 15 minutes each.
set -euo pipefail
cd "$(dirname "$0")/../data"
BASE=http://archive.routeviews.org/route-views.linx/bgpdata

get() { [ -s "$(basename "$1")" ] || curl -fSLO --retry 3 "$BASE/$1"; }

# 2.2 Level 3 leak: before (14:00) and after (18:00) on 2017-11-06
get 2017.11/RIBS/rib.20171106.1400.bz2
get 2017.11/RIBS/rib.20171106.1800.bz2

# 2.3 Egypt: RIB just before the shutdown, plus updates 21:00-22:45 (covers 21:00-23:00)
get 2011.01/RIBS/rib.20110127.2000.bz2
for hh in 21 22; do
  for mm in 00 15 30 45; do
    get 2011.01/UPDATES/updates.20110127.$hh$mm.bz2
  done
done
ls -lh
