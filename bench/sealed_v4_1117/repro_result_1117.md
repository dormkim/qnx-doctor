# Reproducibility check — v4 (2026-11-17, before scoring)

bench/repro_v3.py pool answers/labels.json repro_20261117.json --same-boot, no doctor, H2 harness (same-boot TICKS/TICKS2).

## Result: STOPPED — harness failure, not scored (README rule 2 stop rule)

- Reproduced (agree): 19 / 24.
- Disagree: 5 — D08, D13, D17, D20, D23. Every one is "expected stops, kept ticking": a role the answer key marks as hung kept making progress.
  - priority_chain: D08, D13, D17, D23 (4)
  - multi (priority inversion + spin): D20 (1)
- Stop rule (2 or more priority_chain fail reproduction for a harness reason) triggered (4). The run is not scored.

## Likely cause (not yet fixed)
The chain scenarios did not starve their low-priority waiter: the counts grow 15-21 ticks in the window (free progress), not a stall. This matches the v3 caveat (docs/measure_structure_1116.md "Chains are sensitive to host load"; scenario processes inherit priority 50 from hi, so an intended priority gap may be flattened). Whether it is the launcher priority, host load, or the independent author's chain design is the next thing to examine on dev — as v3 also left "why the chain appeared" open.

## Next
Fix chain reproduction on dev (document the harness change here; the seal's scenarios and answers are unchanged, scenarios-only hash 547cfa55). Re-run this check. Score only after at most 1 priority_chain fails reproduction.
