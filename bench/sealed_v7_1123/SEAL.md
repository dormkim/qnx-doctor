# Seal: v7 patch set

Sealed 2026-11-23 (KST), after `v7-freeze` and before any `verify` run on these patches. **55 patches** against the 14
v6 hang scenarios without a mutex wait (bases identical to `bench/sealed_v6_1123/pool`, checked with `diff -r`).

| What | sha256 |
|---|---|
| labels_author.json | `c6f54cb7add0983a6f26bea97201e8093d2cde1ec5511ef008cdbd0625e2a987` |
| patches/ (tree) | `3a741531c896b026940c7fdaa5a5c2c4f8c5c7e4e389957aa3165d410ca4be5c` |

Author: a fresh agent in a plain folder (no git) with only the 14 bases, the harness and the brief
(V7_VERIFY_PLAN section 3). Its report and file list: `README_author.md`. What it said it did outside the rules: it
copied `base/` once to a scratch folder on the maintainer's Mac to make diffs with `diff -u` (deleted afterwards
by the maintainer, not opened), and it once started `python3` with an empty script on the server. It read the header
comments of `common/qd_trace.c`, which describe how message pairs are recorded; it says it built no patch around them.

Second reader: a fresh agent with the bases and the diffs only (no labels, no author README), started before this
seal. Its labels (`labels_reader.json`) are committed before scoring; it never sees the run.
The maintainer opened none of the patches or labels before this seal.
