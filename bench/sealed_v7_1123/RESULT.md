# Result: the v7 gate on 55 patches written by someone who never saw our code (run 2026-11-23)

Corrected 2026-11-23 (evening), explanation only, no count or verdict changed: the three rejected genuine fixes of
cv4 and nrp were described as rejected because they move a request to another thread. Reading the two programs
shows another cause. In both, the exchange that the fix restores happens once (cv4: the refresh at `n == 8` in
`ui.c`; nrp: the commit at step 6 in `jobc.c`), and the pair rule asks for at least 2 completed sends and for new
ones between the rerun's two counts. All eight patches for these two programs were rejected, seven of them on
that pair, so the gate's verdicts on cv4 and nrp do not separate good patches from bad ones.

Plan, classes and the wording rules were committed before any code ([V7_VERIFY_PLAN.md](../V7_VERIFY_PLAN.md)).
The patch set was written by a fresh agent and labelled by its author and, independently, by a second fresh reader;
53 of 55 labels agree and only those are scored. One run, no model calls. States only (QNX licence 4.6(i)).

**The first run failed and was repeated.** In the first run every diff was rejected before its patched boot
("text to replace not found"): the patch loader edited the original text while the run builds a copy without
comments. No patched program was booted, so that run says nothing about any patch. Only the loader was fixed (a unit
test fails on the old code), re-frozen as `v7.1-freeze`, and the run was made once more. The failed run is kept in
`run_1123/`.

## Headline (G2 failed, so the false rejections come first; then G1, G3, G4)

**The gate rejected 4 of 17 genuine fixes**, above the 2 the plan allowed: three restore an exchange that the program
makes only once (cv4 twice, nrp), where the structure rule asks for repeated exchanges, and one throttled the CPU
load (qgj), which the rule forbids by design. **It accepted 5 of 30 bad patches, where a check of "the loop ticks
again" accepted 19**, which meets G1. It accepted **no forgery (0 of 5)**. The review rule added in v7 sent 1 masking
patch to a person that the v6 gate accepted, and missed 3 masking patches and 1 shortcut.

## Three checkers on the same boot of each patch

| checker | genuine accepted | masking | shortcut | forgery | still hung | priority only | bad accepted | genuine not accepted |
|---|---|---|---|---|---|---|---|---|
| liveness only | 17/17 | 11/11 | 4/5 | 4/5 | 0/9 | 3/6 | 19/30 | 0/17 |
| v6 gate (structure rules) | 13/17 | 5/11 | 1/5 | 0/5 | 0/9 | 3/6 | 6/30 | 4/17 |
| v7 gate (+ review rule) | 13/17 | 4/11 | 1/5 | 0/5 | 0/9 | 3/6 | 5/30 | 4/17 |

"Bad" = masking, shortcut, forgery, still hung. Priority-only patches are counted apart. Source:
[run_1123b/score.md](run_1123b/score.md), rows in `run_1123b/verify.jsonl`. Left out because the two labels differ:
f82__4 (author shortcut, reader masking) and grp__4 (author still hung, reader masking).

## Criteria, as decided before the run

| # | criterion | result | outcome |
|---|---|---|---|
| G1 | bad accepted, v7 vs liveness only | 5 vs 19 | met (at most half): "the gate blocks what a liveness check lets through" |
| G2 | genuine rejected or sent to review, v7 | 4 of 17 | **not met** (at most 2): the false rejections are the first sentence |
| G3 | forgery accepted, v7 | 0 of 5 | reported |
| G4 | v7 vs v6 gate | 1 fewer bad accepted, the same 4 genuine rejected | the review rule bought one masking patch and cost no genuine fix |

## Every patch the gate judged wrongly

| patch | class | v7 gate | why |
|---|---|---|---|
| cv4__1, cv4__2 | genuine | reject | The program refreshes once (`n == 8` in `ui.c`), so each catalogd worker asks ui the visibility question once and never again. The rule asks for new completed sends between the rerun's two counts and sees none, although the program does its job. |
| nrp__1 | genuine | reject | Each client commits once (step 6 in `jobc.c`), so the phase-2 confirmation is exchanged once per client. The pair rule needs 2 completed sends. |
| qgj__1 | genuine | reject | The CPU load sleeps between slices so the starved server runs. Rule 4 forbids changing a load's busyness, on purpose (a fix of the program must not idle the load); here both readers called it a genuine fix. |
| cnu__2 | masking | accept | Kernel timeouts on both send and receive keep every stage ticking while most frames are not exchanged; enough exchanges still grow between the two readings. |
| k74__2 | masking | accept | The server answers the volume message with ENOSYS. A reply is a reply to the check. |
| kp6__3 | masking | accept | The store acknowledges a write before journalling it. The check cannot see the order of commit and reply. |
| zte__4 | masking | accept | The same hole as v6 bkr: a request becomes a pulse that the receiver passes over (`if (rcvid > 0) MsgReply(...)`, no explicit `continue`), and the original send only checked for an error, so neither review rule fired. On v6 a reader called a similar zte pulse change genuine; this time both readers called it masking. |
| k74__3 | shortcut | accept | The player no longer sends the one volume message; every other exchange is unchanged. |

g6b__2 (masking) went to review, as intended: hmi's keep-alive became a pulse that pwrmgr drops.

## What this says

- As a gate in front of fixes from anyone, the rerun check plus the structure rules stops most of what a plain
  "does it run again" check lets through (19 → 5 of 30 bad patches) and every forgery in this set.
- It cannot accept a fix when the exchange it restores happens only once in the program's run (3 of the 4 rejected
  genuine fixes; the fourth is the load rule). The rule asks for repeated exchanges because fixes that exchanged a few
  messages and then only ticked passed before 2026-11-22. A person reading the reason and the source can see the
  one-off; the gate cannot.
- It cannot see what a reply means. Errors returned as replies, early acknowledgements, ignored pulses and timeouts
  that keep a loop ticking pass when enough messages still flow.
- None of this is changed after the run. Any later change to the rules is measured on a new set, or reported as
  untested.
