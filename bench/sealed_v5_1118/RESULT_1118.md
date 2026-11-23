# Sealed set v5: result of the single scoring run (2026-11-18)

Translated on 2026-11-23 from the Korean working note `bench/sealed_v5_1118/결과_1118.md`, which is kept unchanged beside it because sealed files cite it by name. This English text is the version we submit.

After the harness fix (the `/dev/shmem` rename bug, 647c90d), the **priority-inversion detector was measured again on a new sealed set**. Single core, 4 arms, one run only. The seal, the repro check (12/12) and the hashes are in `SEAL.md`.

## Headline: v4's 0/5 became 4/4

| arm | kind found | priority_chain | unknown | false alarm | first fix | fixed (retries included) |
|---|---|---|---|---|---|---|
| code | **10/12** | **4/4** | **2/2** | 1/2 | - | - |
| ai (ours) | **10/12** | **4/4** | **2/2** | 1/2 | 4/10 | 4/10 |
| naive | 8/12 | 4/4 | **0/2** | 0/2 | 4/10 | 4/10 |
| naive_x2 | 8/12 | 4/4 | **0/2** | 0/2 | 4/10 | 4/10 |

- **priority_chain 4/4** (v4 was 0/5). With the rename bug fixed, the inversion really forms, and the wait-graph detector proves it as it is. Once the inversion exists, naive also gets 4/4, so our advantage is not "we name the inversion better". (Corrected 2026-11-21: the original said «naive (pidin guess)». naive is not given pidin. It reads only the source and the TICK counts per role, `bench/naive_hang.py` header.)
- **Our advantage = the honesty axis.** Kind found is 10/12 vs naive 8/12, and the whole 2-point gap is **unknown 2/2 vs 0/2**: on E11 (CPU spin) and E12 (permanent semaphore wait), ours **declares it is outside the provable range** with 「not a message deadlock (unknown)」, and naive lets it pass as 「none」 and misses. deadlock and missing_reply are full marks in all four arms (controls).

## Two honest flaws (not re-scored; sealed, one run)

1. **healthy 0/2 is a scorer vocabulary problem (not a real failure).** The tool outputs `none` (no deadlock) on healthy scenarios, and `hit()` in `score_structure.py` does not count that `none` as a "healthy hit" (the same none↔healthy vocabulary gap as v4). **On E09 (healthy relay) ours output exactly `none`**, which is a safe reading as healthy, and the 0/2 in the table undercounts. Changes after the seal are not allowed, so **the scorer is not fixed; it is only recorded here**.

2. **The "1 false alarm" on E10 is not a detector flaw but a design mistake in my scenario.** I built the "harmless background load" of E10 as a **dead infinite spin** (`for(;;)` after one tick). The tool flagged, **rightly**, "this process is RUNNING in every snapshot but the loop makes no progress → spinning/unknown" (output: `unknown (spinning): ... 204821(load) is running ...`). **It did not invent a deadlock or an inversion** (0 claims of deadlock/chain). A fair design would make the load advance (tick) periodically, or let the E10 label allow `unknown`. To be corrected in the next set.

## Value of the AI layer
- **Zero contribution over code in both detection and fixing**: kind code 10/12 = ai 10/12, fixes ai 4/10 = naive 4/10 = naive_x2 4/10.
- The AI's measured unique value is still **"it says it does not know + zero wrong fixes"** (false fix 0, unknown 2/2).
- **Fixing the send cycle (deadlock) is 0/2 in all four arms.** (Corrected 2026-11-21: the original said «a fix that changes it to an asynchronous pulse is hard», which does not match the record. In the record (E05 and E06 in `scored_1118/*.jsonl`), all three arms gave a fix in the first attempt that changes it to a pulse, and on re-run there was no cycle, the process count was the same, TICK grew a lot, and the structure check reason was empty. What did not pass was the judging rule «at least one role that had TICK 0 at first must exist». This ring prints one TICK in every role before they all stop. E08 (missing reply) is the same for that reason. The rule was fixed on 11/21, and this table is not drawn again. The dev set recalculation is in `bench/DEVSET_RECALC_1121.md`.)

## Conclusion
The claim 「proving AI + unknown-saying AI」 **stands on numbers this time**: priority_chain 4/4 + unknown 2/2 beats naive 10:8. The 0/5 in v4 was a harness bug, not the detector (SEAL.md Correction 3), and the new sealed set, with that bug fixed, shows this. The remaining weak points are (a) the AI adds nothing over code in detection and fixing, and (b) send-cycle fixing 0/2. Both are tasks for the next set and lever. (Added 2026-11-21: (b) was a problem of the judging rule, not of the fix; see the correction in «Value of the AI layer» above. The 2 points of «10:8» come from the comparison arms having no answer «unknown». v5 is now used as a development set, and the number to use in a claim is measured once on v6: `bench/V6_PLAN.md`.)
