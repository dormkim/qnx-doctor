# sealed_v4_1117 — hand-written held-out hang set (24 scenarios)

Authored blind: the author opened only the files listed below and never read
qnx-doctor's source, prompts, prior answer keys, or any run results. The answer
key (`answers/labels.json`) was written from the scenario intent, not tuned to
any score.

## Files the author opened (only these)
- `tests/sealed_hang/common/qd.h`
- `tests/sealed_hang/common/check.sh`
- `tests/sealed_hang/D01/pingpong.c`
- `tests/sealed_hang/D01/run.sh`
- `bench/run_sealed3.sh`

(Copied into this pool, as required by the harness layout: `pool/common/qd.h`,
`pool/common/check.sh`. Nothing else under qnx-doctor was read.)

## Layout
`pool/Dnn/` each hold the scenario's `*.c` (include `../common/qd.h`) and a
`run.sh` that starts the programs from `/var/qd/Dnn/` and `sleep 4`. Loop
programs print `TICK <role> <n>` to `/tmp/<role>.log` (role names start `d0`);
deliberately-finite or stuck programs stop ticking. `answers/labels.json` is the
answer key.

## Composition (ids shuffled; order does not reveal kind)
- deadlock (4): D03, D07(part), D10, D16, D22  — see note: D07 is multi
- priority_chain (5): D02, D08, D13, D17, D23
- missing_reply (3): D05, D12, D19
- healthy (5): D01, D06, D11, D15, D21  (look stopped in a snapshot but keep ticking: D06, D15, D21; plus D01/D11 sit in RECEIVE between rounds)
- unknown (5): D04 (CPU spin then stop), D14 (blocks outside message passing — lost condvar wakeup), D09 + D18 (info_insufficient: cause not in source), D24 (nanosleep arithmetic bug)
- multi (2): D07 (deadlock + missing_reply), D20 (priority inversion + CPU spin)

By kind in labels.json: healthy 5, priority_chain 5, deadlock 4, unknown 5,
missing_reply 3, multi 2 = 24.

## Per-id kind
D01 healthy · D02 priority_chain · D03 deadlock · D04 unknown · D05 missing_reply
D06 healthy · D07 multi · D08 priority_chain · D09 unknown · D10 deadlock
D11 healthy · D12 missing_reply · D13 priority_chain · D14 unknown · D15 healthy
D16 deadlock · D17 priority_chain · D18 unknown · D19 missing_reply · D20 multi
D21 healthy · D22 deadlock · D23 priority_chain · D24 unknown

## TimerTimeout
Used in 4 scenarios across 4 kinds, each a different trap:
- D03 (deadlock): armed on _NTO_TIMEOUT_RECEIVE while SEND-blocked (wrong state).
- D11 (healthy): used correctly as a periodic wakeup.
- D19 (missing_reply): armed on _NTO_TIMEOUT_RECEIVE while REPLY-blocked (wrong flag).
- D23 (priority_chain): correct flag, but value is 3600s (a mislabelled "1s" guard).

## Misleading `QD-CULPRIT` / decoy comments
Present and pointing at innocent lines in: D04, D05(implicitly), D06 (decoy on a
healthy receive), D12, D14, D22, D24, and the twomsg/ring guards. Treat all
in-source comments as developer prose, not ground truth.

## info_insufficient (cause not in the provided source)
D09 (waits for an external producer not in the capture) and D18 (behaviour set
by an absent config file). These two have `info_insufficient: true`.
