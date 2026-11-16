# First measurement — 2026-11-15 (internal scenarios only)

Scenarios: `scenarios/internal/I01–I04`, built from our own 11/14 failures (QEMU unpacked without root, mkqnximage rebuild).
«Solved» = the doctor's fix was applied by code and the original command was **re-run successfully** (boot marker seen / verify passed). A fix that does not pass the rerun is never reported as solved, so «claimed solved but still broken» is 0 by construction.

| Mode | Solved (proven by rerun) | Notes |
|---|---|---|
| Rules only (no AI) | 3/4 | Rule table was written by us after hitting I01–I03, so this number is biased upward. I04 has no error message ("Nothing to do"), so no rule fires. |
| AI only (no rules) | 4/4 | Each case: 1–2 read-only probes; I04 also searched the local QNX docs (mkqnximage page) and chose `--build`, which the rerun proved. |
| Rules + AI | 4/4 | Rules solved I01–I03, AI solved I04. |

Caveats: 4 cases only, and they are our own failures. The fair comparison is the **sealed external set** (`tests/sealed/`, 11 runnable, committed before tuning in 5657ce3) — not run yet; it will be run once.
Model: claude-opus-5-5 (adaptive thinking), local docs index of the user's SDP install (5,134 pages, not redistributed).
No QNX performance numbers are published (QDL 4.6(i)); only the doctor's own diagnosis results.
