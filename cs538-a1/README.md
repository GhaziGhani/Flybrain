# CS 538 A1 – Part 2: BGP analysis (working folder)

Pipeline for the BGP option of the assignment. Data comes from the Route Views
LINX collector (`route-views.linx`).

## Layout

| Path | What it does |
|---|---|
| `tools/fetch_data.sh` | Downloads the 4 RIBs/updates needed (2017-11-06 RIBs, 2011-01-27 RIB + updates 21:00–22:45) into `data/` |
| `tools/bgpdump/` | RIPE NCC bgpdump, built from source (not committed, see Setup) |
| `tools/netflix_paths.py` | Counts distinct AS paths to `198.45.49.0/24` in a RIB dump; flags paths via AS3356 |
| `tools/egypt_parse.c` | Stand-in for the course's `simple_bgp_parse.c`: marks prefixes whose **origin AS** is Egyptian, then prints `time running_total` for each withdrawal of one |
| `tools/plot_withdrawals.py` | Plots the cumulative withdrawal curve (matplotlib instead of gnuplot) |
| `run_bgp.sh` | Runs all of the above; writes into `results/` |

## Setup

```bash
git clone --depth 1 https://github.com/RIPE-NCC/bgpdump.git tools/bgpdump
(cd tools/bgpdump && ./bootstrap.sh && make)
gcc -O2 -Wall -o tools/egypt_parse tools/egypt_parse.c
pip install matplotlib
tools/fetch_data.sh      # needs access to archive.routeviews.org
./run_bgp.sh
```

## bgpdump `-m` field reference (Q 2.2.2)

`TABLE_DUMP2|time|B|peer_ip|peer_as|prefix|as_path|origin|next_hop|local_pref|med|communities|atomic_agg|aggregator|`

- `TABLE_DUMP2` = RIB entry; `BGP4MP` = update message (type `A` announce / `W` withdraw / `STATE`)
- `peer_ip`, `peer_as` = the router that gave the collector this route
- `as_path` = ASes traversed, nearest first; **last AS = origin** (owner of the prefix)
- `origin` = IGP/EGP/INCOMPLETE; `next_hop`; `local_pref`; `med` = multi-exit discriminator
- `communities` = operator tags; `atomic_agg` = AG/NAG; `aggregator` = AS + IP that aggregated the route

## Concepts to understand for the write-up

- **Distinct AS paths**: the collector has many peers, so one prefix appears in
  several RIB entries. Count unique `as_path` strings, not lines.
- **Peering vs. transit**: in a *transit* relationship a customer pays a
  provider to reach the whole Internet. In *settlement-free peering*, two
  networks exchange traffic only for their own and their customers' prefixes,
  and **do not re-advertise routes learned from one peer to other peers or
  providers** (the "valley-free" export rule). Breaking that rule is a *route
  leak*. Compare the 18:00 paths with the 14:00 ones to see which rule Level 3 broke.
- **Origin AS**: a prefix is "Egyptian" if an Egyptian AS *originates* it (last
  AS in the path), not if an Egyptian AS merely appears in the path.
- **Withdrawal storm**: the steep section of the cumulative curve; its length is
  the time between where the slope rises and where it flattens again.
