# Sealed external set — single scored run (2026-11-15)

Set: `tests/sealed/` (13 cases from public QNX docs/release notes/forums, sealed in 5657ce3 before tuning). Run once per mode on the server, no changes in between. Raw: `runs/sealed_{rules,ai-only,ai}_1115.jsonl`, reproducibility: `runs/sealed_repro.json`.

**Reproducibility (checked first, outputs not read):** 8 of 11 runnable cases actually fail on our SDP 8.0.0 server. X06, X09, X10 did **not** fail (the command succeeded as written) → excluded. X12–X13 recorded only (8.0.2 path change; would need wrong credentials).

| Mode | Solved, proven by re-run (of 8) | «Solved» but actually broken |
|---|---|---|
| Rules only (no AI) | 2 (X01, X04) | 0 |
| AI only (no rules) | 4 (X01, X02, X04, X08) | 0 |
| Rules + AI | 4 (rules X01·X04, AI X02·X08) | 0 |

**The 4 unsolved cases are not fixable by design** (truth labels: unsupported ARMv7 target, a signal flag that the case's public source lists as unavailable, unsupported mkqnximage arch/platform combo, aarch64 binary on x86_64 target). In all 4 the AI **gave up with an explanation** instead of claiming a fix; reading its text against the truth label, each explanation names the actual cause (human judgement, 4/4 — the scorer's exact-label column cannot score free text). No fix was claimed for any of them.

What this means for the video: «AI off 2/8 → AI on 4/8 solved, 0 false "solved", and the other 4 correctly explained as unfixable».
Caveats: 8 cases, one run. The rule table was written before seeing these cases; the AI prompt too. **Any change made after reading these results needs a new sealed set** to be measured fairly.
No QNX performance numbers (QDL 4.6(i)).
