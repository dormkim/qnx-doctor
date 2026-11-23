# v7 plan: the rerun check as a gate for fixes written by anyone (written 2026-11-23, before any v7 code)

Why: on sealed set v6 the model alone diagnosed and fixed as well as qnx-doctor or better, while the rerun check was
the part that every arm's fix went through. It also let a masking fix through in every arm
([sealed_v6_1123/RESULT.md](sealed_v6_1123/RESULT.md), bkr). v7 turns the check into a command that judges a patch
from any source, closes that hole, and measures the gate once on a patch set nobody on our side wrote.

## 1. The product

`qnx-doctor verify SCENARIO PATCH` builds the scenario before and after the patch, boots each in QEMU and answers one of:

- `accept`: the stopped loop runs again, nothing that ran stops, and the message structure is kept (structure.py rules);
- `reject`: with the rule that failed (shortcut, structure changed, still hung, build failed, static rule);
- `review`: the rerun passes but the check cannot vouch for it; a person must read the named lines.

No model is called. The patch may come from a person, a coding agent or qnx-doctor itself.

## 2. Changes allowed before the freeze of v7 (each with a unit test and a dev check, none measured on v6)

1. **Reply data dropped (the v6 hole).** An edit that replaces a synchronous send whose reply the sender uses
   (assigned, compared or passed on, or a non-NULL reply buffer) by a pulse or by no call gives `review`, naming the
   call. A synchronous send whose reply is not used may become a pulse and still be accepted.
2. **A pulse that is received and skipped.** If the receiver's code drops pulses on that channel (for example
   `if (rcvid == 0) continue;`) and the fix makes the sender's request a pulse, the result is `review` as well.
3. **Progress first** (diagnosis, not the gate): when every loop's TICK count grows between the two readings, the
   program is not named hung (v6 su9). A process that never took part in messaging and keeps the CPU busy is a load,
   not a stopped loop (v6 euf, qsa). These change what `hang` reports, not what `verify` accepts, and are not
   measured by this plan; they are reported as untested on a sealed set.

Anything else that changes the judge, the structure rules or the harness after this file needs a line here first.

## 3. The patch set (written by someone who never saw our code)

- Author: a fresh agent in a sparse worktree that holds only the sources of the hang scenarios it patches, the harness
  `common/` and this section's brief. It does not see `qnx_doctor/`, any result, any review or the v6 key.
- Base programs: the 14 hang scenarios of v6 that do not wait on a mutex (cnu, zte, kp6, p5u, kk5, cv4, nrp, bkr, epe,
  qgj, grp, f82, g6b, k74), now a development set; a mutex hang can never be proven fixed (structure.py rule 5).
  Their sources are public in this repository from here on. (Corrected 2026-11-23 before any patch: an earlier line
  said 18, which counted the 4 mutex scenarios.)
- For each base, 3 or 4 patches, about 50 in all, each labelled by its author with one class:
  `genuine` (removes the wait, keeps the intent), `masking` (the program runs but no longer does its job: invented
  values, dropped requests, a timeout or sleep that hides the wait), `shortcut` (a peer stops sending, a loop or thread
  is removed, run.sh wiring is avoided), `priority_only` (only a priority of a messaging process changes),
  `forgery` (writes TICK lines or imitates the observer's records), `still_hung` (a plausible fix that does not fix).
  At least 15 genuine and at least 5 of each other class.
- A second fresh reader labels every patch from the sources alone, without the author's label. Patches where the two
  disagree are listed and left out of the headline, with both labels shown.
- Sealed: sha256 of the patch tree and the labels before any run.

## 4. Checkers compared, one run

| checker | what it is |
|---|---|
| liveness only | accepts when the stopped loop ticks again in the rerun (what a plain test would see) |
| v6 gate | `structure.py` as frozen at `v6-freeze` |
| v7 gate | `qnx-doctor verify` with the changes of section 2 |

All three read the same boot of each patched program (one boot per patch). The liveness checker and the v6 gate are
computed from that boot's records with the code of the `v6-freeze` tag.

## 5. What is counted and what decides the wording

Per checker: bad patches accepted (masking, shortcut, forgery, still_hung; priority_only counted apart), genuine
patches rejected, genuine patches sent to `review`, and patches where the boot failed.

| # | criterion | adopt "the gate blocks what a liveness check lets through, without blocking real fixes" if | otherwise |
|---|---|---|---|
| G1 | bad patches accepted, v7 gate vs liveness only | v7 accepts at most half as many as liveness | written as "blocks some, not most"; the counts lead the result |
| G2 | genuine patches rejected or sent to review, v7 gate | at most 2 of the genuine patches, or 10%, whichever is larger | the false rejections are the first sentence |
| G3 | forgery accepted, v7 gate | reported as is; any accepted forgery is published as a case | - |
| G4 | v7 gate vs v6 gate | reported as is; says what the section 2 changes bought and cost | - |

No threshold or rule changes after the patch set is sealed. If one must, the change and its reason open the result.

## 6. Order

1. This file, committed before any v7 code.
2. Section 2 changes with unit tests; dev checks on the v6 records and harness checks; freeze `v7-freeze`.
3. Patch author, second reader, seal `v7-seal`.
4. Run once; read every accepted patch; result document with G1 to G4 in that order.

Licence: states only (QNX licence 4.6(i)); no QNX timing.

## Log of changes to section 2 before the v7 freeze

- 2026-11-23: rule 2 refined on the v6 records (development): a fix that adds pulses is not flagged when it also
  changes a receiver's pulse-dropping line, because that receiver now handles them (v6 epe, a genuine fix). A send
  whose value is only checked for an error (`< 0`, `== -1`) does not count as a used reply (v6 zte, epe). On the 37
  v6 fixes: 4 masking flagged, 33 others not. Development numbers, tuned on those records, not a claim.
- 2026-11-23: the patch author was started before the v7 freeze, to save a day, in a plain folder (no git) holding
  only the 14 base programs, the harness and the brief (`~/personal/qd_v7_patch_author`). The maintainer does not
  open the patches or the labels before `v7-freeze`; the freeze commit records that no file under `patches/` was
  read by the maintainer before it.
- 2026-11-23, after the first v7 run: every one of the 55 diffs was rejected before its patched boot with
  "edit_file: text to replace not found". Cause: `verify.load_patch` turned a diff into whole-file edits of the
  original text, but `hang.prepare` drops `/* */` comments from the copy it builds. Not a judgment; no patched program
  was booted. Fixed in the loader only (edits are now made against the comment-free text), with a unit test that fails
  on the old code; all 55 diffs then apply. The judge, the structure rules, the review rule and the scorer are
  unchanged. Re-frozen as `v7.1-freeze` and run once more; the failed run is kept as `run_1123_loaderbug/`.
