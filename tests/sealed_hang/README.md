# Sealed hang set (2026-11-15)

Seven QNX 8.0 message-passing scenarios, written **before** the hang collector, judge and AI prescriber existed.
Five are real faults (2-way and 3-way SEND cycles, a REPLY chain behind a cycle, a synchronous callback cycle, a priority-inversion chain on a fixed-priority channel); two are normal systems that must NOT be reported as hangs (false-positive check).

Rules
- Labels in `labels.json` are the answer key. Do not edit them to match results; a changed set needs a new seal.
- Reproducibility is checked first without reading the doctor's output (does the loop stop / keep ticking).
- The set is run once for the measurement; fixes found while looking at results are measured on a new set.
- Only states are reported (blocked/running, TICK or not). No latency or timing numbers are published (QNX licence 4.2(i)).

Run on target: `/var/qd/hi /var/qd/check.sh Dxx` (`hi` = run the observer at priority 50; added before the first run, labels unchanged) → pidin snapshot (taken at priority 63 by `snap`) + TICK counts per role.
