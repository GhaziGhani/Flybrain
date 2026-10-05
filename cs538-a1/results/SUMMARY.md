# Results (Route Views LINX)

## 2.2 Netflix 198.45.49.0/24
| Snapshot | RIB entries | Distinct AS paths | Via AS3356 |
|---|---|---|---|
| 2017-11-06 14:00 (before) | 2 | 1 | 0 |
| 2017-11-06 18:00 (after)  | 15 | 13 | 12 |

- Before: `37271 6762 2906` (the only path)
- After, shortest leaked: `6453 3356 2906`
- After, longest (10 hops): `41695 6067 6067 6067 6067 6067 6067 2914 3356 2906`.
  AS6067 appears 6 times = AS-path prepending.
- Common to all new paths: `... 3356 2906`, i.e. Level 3 immediately before Netflix.

Full lists: `netflix_1400.txt`, `netflix_1800.txt`.

## 2.3 Egypt, 2011-01-27
- Update files 20:50-23:07 UTC: 1,680,323 update messages (235,491 withdrawals)
- First update 20:50:54, last 23:07:49 UTC, average 204.5 updates/s
- RIB 19:19: 2,526 prefixes originated by AS 5536/8452/24835/24863/36992
- Egyptian withdrawals seen: 129,057 (each prefix withdrawn by many LINX peers)
- Background rate before 22:11: roughly 100-900 per minute
- Storm: begins ~22:12 (2,660/min), peaks 22:25 (10,410/min), ends ~22:41-22:43
  (back below 1,000/min, near zero from 22:44) -> about 30 minutes
- Plot: `egypt_withdrawals.png`; raw data: `egypt_withdrawals.dat`
