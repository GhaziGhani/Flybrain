#!/usr/bin/env bash
# Run the whole BGP part end to end. Requires the data from tools/fetch_data.sh.
set -euo pipefail
cd "$(dirname "$0")"
BGPDUMP=tools/bgpdump/bgpdump
D=data; R=results
mkdir -p "$R"

echo "### 2.2 Netflix 198.45.49.0/24 before (14:00) and after (18:00)"
$BGPDUMP -q -m $D/rib.20171106.1400.bz2 | python3 tools/netflix_paths.py | tee $R/netflix_1400.txt
$BGPDUMP -q -m $D/rib.20171106.1800.bz2 | python3 tools/netflix_paths.py | tee $R/netflix_1800.txt

echo "### 2.3.1 Unmodified behaviour: count all updates"
for f in $D/updates.20110127.*.bz2; do $BGPDUMP -q -m "$f"; done \
  | tools/egypt_parse > /dev/null 2> $R/updates_summary.txt
cat $R/updates_summary.txt

echo "### 2.3.3 RIB + updates -> cumulative Egyptian withdrawals"
{ $BGPDUMP -q -m $D/rib.20110127.2000.bz2
  for f in $D/updates.20110127.*.bz2; do $BGPDUMP -q -m "$f"; done
} | tools/egypt_parse > $R/egypt_withdrawals.dat 2> $R/egypt_summary.txt
cat $R/egypt_summary.txt
python3 tools/plot_withdrawals.py $R/egypt_withdrawals.dat $R/egypt_withdrawals.png
