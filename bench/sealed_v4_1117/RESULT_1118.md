# sealed hang v4: scored result (2026-11-18)

Translated on 2026-11-23 from the Korean working note `bench/sealed_v4_1117/결과_1118.md`, which is kept unchanged beside it because sealed files cite it by name. This English text is the version we submit.

Single scored run, 4 arms (code / ours=ai / naive / naive_x2), same model, one QEMU at a time, `QD_SMP=1`.
Run output frozen in `scored_1118/*.jsonl`. States only (QNX licence 4.6(i)); no timing numbers.

## Scorer change after the seal (documented per V4_PLAN)

The arms ran clean, but `score_structure.py` crashed tallying (`KeyError: 'healthy'`): the independent author's
labels use the kinds **`healthy`** (5) and **`multi`** (2), while the scorer's vocabulary was
`(deadlock, priority_chain, missing_reply, none, unknown)`. Fixed by aligning the scorer to the sealed labels.
`healthy` takes the no-fault / false-alarm-baseline role the scorer gave `none`, and `multi` is added as a fault
kind (with its own column). The change is symmetric across all arms and does not touch any arm's frozen output;
only the tally was recomputed on the existing `*.jsonl`. Commit recorded below.

## Headline (honest)

| arm | kind found | deadlock | prio chain | missing reply | multi | healthy | unknown | false alarm | fixed (retries) | false fix |
|---|---|---|---|---|---|---|---|---|---|---|
| code | 12/24 | 2/4 | 0/5 | 3/3 | 2/2 | 0/5 | 5/5 | 0/5 | - | 0 |
| **ours (ai)** | 12/24 | 2/4 | **0/5** | 3/3 | 2/2 | 0/5 | **5/5** | **0/5** | 5/19 | **0** |
| naive | 13/24 | 4/4 | **4/5** | 3/3 | 2/2 | 0/5 | **0/5** | 0/5 | 4/19 | 0 |
| naive_x2 | 11/24 | 4/4 | 3/5 | 3/3 | 1/2 | 0/5 | 0/5 | 0/5 | 5/19 | 0 |

**Ours does not beat the naive baseline on detection.** On every priority-starvation scenario (D02/D08/D13/D17/D23)
and the D20 multi, ours outputs **`unknown`**. It only claims a hang it can prove from the message wait-graph, and
priority inversion (a server READY-but-preempted, no cycle) is outside that graph, so it declines. The naive LLM
reads the source (channel flags and priority numbers; it gets no pidin) and names `priority_chain` (4/5). It
scores `unknown` 0/5 because it has no word for it: on the 5 unknown labels naive said `none` four times and
`missing_reply` once (D14); naive_x2 said `none` five times.

> Corrected 2026-11-21 against the records (`scored_1118/*.jsonl`). The original text said the naive LLM «reads
> the pidin priorities» and «names a hang on all 5 truly-unknown labels too». Neither matches: the baseline is
> never given pidin (`bench/naive_hang.py` header), and it named a hang on 1 of the 5 (naive, D14), 0 of 5 for
> naive_x2. «Outside that graph» is also only part of the story: in D08, D13, D20, D23 the client never connected
> (Correction 3 in `SEAL.md`), so there was no wait to see; D02 and D17 are mutex waits, which the graph does not
> hold. The table is not rescored; the healthy column 0/5 is a scorer vocabulary error (every arm said `none` on
> all 5 healthy labels) and the «fixed» denominator 19 includes those 5 healthy labels (14 have something to
> fix). v4 is now a development set: `bench/DEVSET_RECALC_1121.md`.

So the measured trade-off is exactly the project's thesis, with the cost shown:
- ours: **0 false alarms, 0 false fixes, `unknown` 5/5** (never misleads), but **prio-chain 0/5** and ties on fixes.
- naive: wins raw detection by guessing, loses the honesty axis (`unknown` 0/5).
- The AI layer adds **nothing over the pure-code wait-graph for detection** (code and ai are identical, 12/24);
  the AI's only measured contribution is on fixes (5/19) and keeping `unknown`/no-false-fix.

## What this says to do next (on a FRESH set; v4 is scored/frozen)

1. **Priority-inversion detector (highest value).** The tool already has the data it needs: the pidin priorities
   show the waiter blocked on a server that is READY/preempted while a higher-priority non-waiter holds the CPU.
   A *provable* rule (not a guess) would turn prio-chain 0/5 → ~5/5 without becoming a guesser like naive. This is
   the clear gap: ours says `unknown` where it could prove `priority_chain`.
2. **Fixes**: ours 5/19 ≈ naive_x2 5/19. The rerun-proven fix loop does not yet clearly beat a two-try naive.
3. Keep the honesty wins (0 FA / 0 FF / unknown 5/5). They are the real differentiator for "Innovation & AI
   Creativity (proving AI + unknown-saying AI)", but detection/fix must improve to claim a top place.

Full per-axis table and literal `unknown` outputs: `scored_1118/score.md`.
