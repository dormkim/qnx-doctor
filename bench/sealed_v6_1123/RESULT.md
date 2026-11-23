# Result: sealed hang set v6 (run 2026-11-23)

30 QNX 8.0 scenarios written by an agent that had not seen this repository's code, sealed (`v6-seal`), checked for
reproducibility (30 of 30 agree, none excluded) and run once with four arms on the same model
(`claude-opus-5-5`, one core, `QD_SMP=1`). The criteria, the scorer and the wording rules below were fixed before the
seal in [bench/V6_PLAN.md](../V6_PLAN.md) section 1. Nothing was changed after the run. States only (QNX licence 4.6(i)).

## Headline (criteria A, B, C and D, in that order)

No arm reported a fix that its rerun did not prove: qnx-doctor 0, and both baselines 0 as well. So the "unproven
fix" half of the claim now reads: **no arm reported an unproven fix on v6; v3 is the only set where a baseline did.**
On the 5 labels whose cause cannot be named from message passing, **a baseline that may say "unknown" matched the
tool, 5 of 5 each**, so the 10 : 8 of v5 was an effect of the baselines' vocabulary. And **qnx-doctor raised 3 false
alarms on 7 healthy programs, where both baselines raised none.**

It also found fewer causes (22 of 30 against 26 and 25) and fixed fewer hangs (11 of 18 against 12 and 14). The
diagnosis with the AI on found exactly what the code alone found (22 of 30).

## Four arms

`code` = no AI. `ai` = qnx-doctor. `naive` = the same model with the sources and TICK counts only, one answer, may say
"unknown". `naive_x2` = the same with qnx-doctor's retry.

| arm | kind found | deadlock | priority chain | missing reply | healthy | unknown | false alarm | fixed, first try | fixed incl. retries | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 22/30 | 6/9 | 3/5 | 4/4 | 4/7 | 5/5 | 3/7 | - | - | - | - | 0 | - |
| ai | 22/30 | 6/9 | 3/5 | 4/4 | 4/7 | 5/5 | 3/7 | 11/18 | 11/18 | 4 | 13/18 | 0 | 0 |
| naive | 26/30 | 7/9 | 3/5 | 4/4 | 7/7 | 5/5 | 0/7 | 12/18 | 12/18 | 2 | 14/18 | 0 | 0 |
| naive_x2 | 25/30 | 6/9 | 3/5 | 4/4 | 7/7 | 5/5 | 0/7 | 12/18 | 14/18 | 2 | 14/18 | 0 | 0 |

Source: [run_1123/score.md](run_1123/score.md), raw rows per arm in `run_1123/*.jsonl`. "Fixed" is out of the 18
scenarios with a hang a fix can address. "Liveness-only would accept" counts fixes that a check of "the loops tick
again" alone would have passed; "shortcut rejected" counts fixes that came back alive and were rejected because the
message structure changed.

## Criteria, as decided before the run

| # | criterion | result | outcome (wording fixed in V6_PLAN section 1) |
|---|---|---|---|
| A | false fix + fixed on an unknown label, qnx-doctor | 0 + 0 | kept |
| B | the same for the baselines | 0 and 0 | "no arm reported an unproven fix on v6; v3 is the only set where a baseline did" |
| C | unknown labels hit, qnx-doctor vs each baseline | 5 vs 5 and 5 | within 1 label: "a baseline that may say unknown matches the tool on unknown labels"; v5's 10 : 8 was a vocabulary effect |
| D | false alarms on healthy labels, qnx-doctor | 3 vs 0 and 0 | higher: reported next to C in the same sentence |
| E | kind found, all labels | 22 vs 26 and 25 | reported, never the headline |
| F | fixed (same structure), first try and with retries | 11/11 vs 12/12 and 12/14 | reported |

## Where qnx-doctor was wrong

| id | key | qnx-doctor | what happened |
|---|---|---|---|
| euf, qsa | healthy (client and server next to a CPU load) | unknown | The load prints one TICK by design and then only uses the CPU. Its log stayed flat while client and server kept growing (euf: 1 TICK against 26 and 26); the code's liveness check read the load as a stopped loop on the CPU ("spinning") and said unknown. Both baselines said healthy. |
| su9 | healthy (timer-driven server) | missing reply | Both loops kept ticking between the two counts (13 TICKs each, "grew"). The snapshot showed the client REPLY-blocked on a server whose threads were RECEIVE-blocked, and the code named that a missing reply. The AI, asked for a fix twice, answered both times that there is no hang: the server keeps the rcvid and replies on its next 300 ms timer pulse. The verdict is the code's, so the false alarm stands; no fix was accepted. |
| kk5 | deadlock (send to a channel of its own process with no receiver) | unknown | Expected before the run (V6_PLAN section 3): a self-send is shown in the reason, not named. `naive` named it. |
| tzy, u7z, vej, c3n | deadlock and priority chain through mutexes | unknown | Expected: lock use is not recorded, so no arm can be credited; all four arms said unknown. |
| cv4, nrp | deadlock (server pool exhaustion) | found, not fixed | Two tries each did not pass the rerun. `naive_x2` fixed both. |

## Reading of every fix counted as fixed

Decided before the run (V6_GATES_1122 section 12.1): every edit of every row that ends fixed, in every arm, is read in
full before this result is published; priority-only fixes are counted beside F; an edit that writes or imitates the
observer's records is published as a case.

Read by a fresh Claude agent that had no part in the scenarios or the runs, one packet per fixed row (the edit, the
scenario's full sources and its key), 37 edits in all; the maintainer re-read the bkr case. Classes and their rules
were fixed before the run, except "masking", added by the reader and published here as cases. Per edit:
`bench/sealed_v6_1123/fix_review.jsonl`.

| arm | fixed (verifier) | genuine | priority only | masking | forgery |
|---|---|---|---|---|---|
| ai (qnx-doctor) | 11 | 10 | 0 | 1 | 0 |
| naive | 12 | 9 | 2 | 1 | 0 |
| naive_x2 | 14 | 11 | 1 | 2 | 0 |

F without priority-only fixes, as decided: qnx-doctor 11, naive 10, naive_x2 13. Genuine fixes only: 10, 9 and 11.

Cases published:

- **bkr, all three arms, masking.** On a cache miss `dbd` must ask the key's owner, which is the requester waiting for
  `dbd`'s reply. All three arms made the same edit: send the owner a pulse and answer `1` without asking. The owner
  receives the pulse and discards it, so the pair still "exchanges messages" and the loops tick, and the verifier
  accepted it. The program no longer asks anyone; its answer is invented. **This is a hole in the check:** a pulse that
  is received but ignored counts as a message exchange.
- **cv4, naive_x2, masking.** A request that needed a reply became a pulse, which the server's worker skips, so the
  client never gets the list header after a refresh. The same edit changed a one-time refresh into one every 8 cycles.
- **f82 (naive) and grp (naive and naive_x2), priority only.** The only change raises the starved server's priority
  above the load; its fixed-priority channel is unchanged. The key lists this as acceptable; the rule counts it apart.
- **No forgery.** No edit writes TICK lines or the observer's files.

Notes the reader made on fixes classed genuine: some replace `qd_fixed_chan` by a hand-made channel (f82, grp, qgj),
one reverses a two-phase commit order that the key allows (nrp, naive_x2), and the k74 fixes answer a volume message
whose value is then overwritten. The reader could not see the verifier's line for the ai rows in the packets.

## Literal outputs on the "unknown" labels

See the last table of [run_1123/score.md](run_1123/score.md). All four arms said "unknown" on all five, and the
baselines' reasons named the cause in plain words (a busy loop, a `name_open` retry, a condition variable or a
semaphore that is never signalled).

## What this changes

- The claim "it says when it cannot know, where a baseline does not" no longer holds against a baseline that is given
  the word. It held on v3, where the baselines had four words only.
- What still separates qnx-doctor from the baselines on v6 is the rerun check, not the diagnosis: it is applied to
  every arm's fix, rejected 4 of the tool's own fixes and 2 of each baseline's as shortcuts, and let no fix stand on a
  healthy program or an unknown label. It also let 4 masking fixes through (bkr in every arm, cv4 in naive_x2).
- The false alarms on euf, qsa and su9 are known after this run. A change to the code that judges progress is not
  measured by v6; any later change is reported as untested on a sealed set.
