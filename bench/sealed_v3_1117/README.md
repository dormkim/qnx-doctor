# Sealed hang set v3 (2026-11-17)

Hand-written QNX 8.0 message-passing scenarios for the «first-seen score» (red team 2026-11-16, fix 3-a; plan item 11/19-21 in
the strategy notes). Written by an agent that **did not read** qnx-doctor's source (`qnx_doctor/`), prompts, verifier, past run results or earlier answer keys (beyond a
one-time print of `tests/sealed_hang/labels.json` key names and truncated values, to learn the format). What it read: this repo's `README.md`,
`tests/sealed_hang/README.md`, `tests/sealed_hang/common/{qd.h,check.sh}`, `tests/sealed_hang/D01`, `D05/run.sh`,
`scenarios/hang_demo/control_loop`, `bench/run_sealed3.sh`, and the
first 80 lines of `bench/score_structure.py` (KINDS and how labels are read, to match the format). Scenarios come from public QNX knowledge (MsgSend/MsgReceive/MsgReply,
pulses, `TimerTimeout`, `_NTO_CHF_FIXED_PRIORITY`, the send hierarchy) and common bug patterns.

## Layout

```
pool/            what the arms see: q01..q21/{*.c,run.sh} + common -> ../../../tests/sealed_hang/common
answers/         the answer key (labels.json). Never inside pool/; only the scorer reads it.
SEAL.md          sha256 of the answer key and of the pool, committed before any run.
```

Every scenario follows the existing format: `run.sh` starts the programs from `/var/qd/<id>/`, loop programs print
`TICK <role> <n>` to `/tmp/d0<role>.log`, other output goes to `/tmp/q_*.err`. Programs include `../common/qd.h`;
some publish a raw channel id in `/tmp/<name>.id`. Ids q01..q21 are in shuffled order; names, comments and log lines
are written as a developer would write them, and some of them are deliberately misleading.

## What the set contains (no per-scenario answers here)

- Faults of the three existing kinds (deadlock, priority_chain, missing_reply).
- Healthy controls built as near-misses: pictures that look like a hang in a snapshot or in the source but keep ticking.
- Multi-cause cases (two independent hangs, or a second hang that only shows after the first is fixed).
- Cases **outside the closed vocabulary**: the loop stops, but not because of a message cycle, a priority chain or a
  missing reply. Some of them cannot be explained from the given sources at all (the cause is outside the scenario):
  the right answer is «not enough information», not a guess.

## Pre-registered rules (fixed before any run; do not change after seeing results)

1. **Run once.** `bench/run_sealed3.sh` with all four arms (code, ours, naive, naive_x2). A fix found while looking at
   results is measured on a new set.
2. **Reproducibility first, without the doctor.** Before scoring, check each scenario's unmodified run against
   `expect` in the answer key (per loop role: `stops`, `ticks`, or `any` with a `_rule`). A scenario whose unmodified
   run disagrees is **excluded with its reason**; its label is not edited. Report the excluded count.
3. **Label `unknown` (outside the vocabulary).** `score_structure.py` knows only
   `deadlock / priority_chain / missing_reply / none`. Before the run, in its own commit, add `unknown` to `KINDS`.
   Hit = the arm names none of the three hang kinds **and** does not call the system healthy (`none`): an explicit
   «can't tell» / «not a message-passing hang». If an arm has no word for that, its literal output is reported and it
   scores 0 on these cases. A «fixed» on an `unknown` case is reported in its own column, not in «fixed» and not as a
   false fix; when the label has `info_insufficient: true`, every such fix is listed for a human to read.
4. **Multi-cause.** A label may carry `accept_kinds`; the kind counts as found if the arm names any of them (naming
   all is noted by hand). «Fixed» needs every stopped loop in `loop_logs` to tick again, as the verifier already
   requires.
5. **Healthy controls** (`none`): any «fixed» is a false fix and must be 0; naming a hang is a false alarm.
6. Report «first try fixed» next to «fixed incl. retries» for every arm, and the per-axis table (labels carry `axes`).
   States only, no QNX timing or performance numbers (QNX licence 4.6(i)).

## Run (server only, detached; one QEMU at a time via the lock)

```
cd ~/personal/qnx-doctor
nohup setsid bench/run_sealed3.sh bench/sealed_v3_1117/pool bench/sealed_v3_1117/answers/labels.json runs/sealed3_<date> > /dev/null 2>&1 &
cat runs/sealed3_<date>/state      # code / fix / done / fail:<why>
```

Verify the seal before running: see `SEAL.md`.
