# v7 freeze (2026-11-23)

Frozen at the parent of this commit, `3fea2fe8e58198f3f79d64f926e73b20409a2103` (branch `v7/verify-1123`). Until the v7 run, the gate
(`verify.py`, `gate.py`), the judge and structure rules, the harness and the scorer do not change.

- `structure.py`, `hang.py`, `hangdoctor.py`, `run_sealed3.sh` and `tests/sealed_hang/common/` are unchanged since
  `v6-freeze` (`git diff --stat v6-freeze`), so the "v6 gate" column of the run is the v6 gate.
- Development checks before the freeze (on v6 records, tuned there, not a claim): the review rule flags the 4
  masking fixes of v6 and none of the other 33; `verify` on four recorded v6 fixes gave review (bkr, cv4) and
  accept (cnu genuine, grp priority only); `hang --no-ai` on the 30 v6 scenarios named 25 right instead of 22
  (su9, euf, qsa now healthy), no other verdict changed.
- The patch author started before this freeze (plan section 6 log). The maintainer has not opened any file under
  `~/personal/qd_v7_patch_author/patches/`; only the number of files was listed.

## sha256

```
8725217c0bffd3a82691fecd720d82074851f89b69979cc6c4dcf7cef39a2682 qnx_doctor/actions.py
48c63136ad35964d1d2a7e15c402e0f9860c20c31f6038d1f623d4ce018a96ed qnx_doctor/ai.py
947568e2f52f04651d6bb985c603f965225921bead27c4017e03b4b354cdf62d qnx_doctor/budget.py
d1c08ccfea3ede86ad482c5a0c2cc5904a40d80b5be952a27b8b53e3a27ff366 qnx_doctor/cli.py
5f61a4d4ae4f0de8bf2122b2211a8eee07710966c91b23570b0ad74efeea709c qnx_doctor/docs.py
885a1f27043e5c08da1f44d89d28fece7870ab78a2f3333dd3ed3ebb916f792a qnx_doctor/doctor.py
05cd55439113577490b3e40490e3f0bbaf71c3bcdce286af94b2d34e27d2f557 qnx_doctor/gate.py
d52486fcc570f5f01cb551c5807802552115facfdf23421b1c7c960d17fec5de qnx_doctor/hangdoctor.py
cdcfc6282f375d2b6e25230b18a34042cd45e2395577da366ae9e21a234d3568 qnx_doctor/hang.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 qnx_doctor/__init__.py
9b01dcc71f53bfd0a0b6c75fac084ef8b027aa37e6dd6e5896322ecfcfa16603 qnx_doctor/live.py
171469dd1acaa5c84903d245a471e46d0793ba5e343cce5eb8766e475e9ad0f2 qnx_doctor/probes.py
085add117d468fe17066e9395922d99b7c7664f5ffd17a8f85d204003bd5d110 qnx_doctor/progress.py
ef2e1f0c42647cbcfcc5cf7dc40961d3ef4815bdf0205e4247fe88d78a0c50ea qnx_doctor/report.py
4d87216ae742861d1f1a44a7f1a736f421f18d149a0fb43e4db586b92d1afc28 qnx_doctor/rules.py
322fb9239fe7f843d3fd49cf3a28d8353b8633fe901b3314cac163d2dbc81e60 qnx_doctor/runner.py
1ed195a5e9efe4eb379d2cd7506a4177fe1a8651813698ca28baa6543a5e3153 qnx_doctor/sandbox.py
115500372445d26597db0376b768b16ab3e0970bf5505d324446f85bc372b3b3 qnx_doctor/source_check.py
01ff6ff54792249036029462a9a50fbbac9599f5bdb34816320a4e6ed630c957 qnx_doctor/structure.py
ef31d8cbb6ba7907fdfbd54a442f1d1f64e154a7a3f803e41b5ec0fbfe80bea8 qnx_doctor/verify.py
ae40ae0982d77370eb2b0c863d732c92482cfbf478e0392928dcce5f41b7e665 qnx_doctor/waitgraph.py
cdd83085abc932ac740744413859984ee3419eed1ad9ce0c3bb70e70d3476220 bench/score_verify.py
1401c0718ff1ec401b8554459b0b1c08a59366409db74aa49cb55b09ae2e9d27 bench/run_sealed3.sh
661dbcd4b4e8f357a6a539513a8df14590391ecd4650f01ce32a78958f7bb613 tests/sealed_hang/common/check.sh
29399c4e58d3bce0af31ce3738f107040052f088f2b843d6e987fd8d5f5c3259 tests/sealed_hang/common/hi.c
0709eca6f142bb7e0a5c96799a63e23c468f3b2a4c8ffa680ec683c1238fa6bf tests/sealed_hang/common/qd.h
153dd030c9fc04e43994b4dcf27b059b13617ca95bd64c64b5508c6035991b14 tests/sealed_hang/common/qd_start.c
2928c152bc8742d87589df8168b1ad589f48bdd1cc101e9feb07094ffa122223 tests/sealed_hang/common/qd_trace.c
8f2e76afc3d40ab68f218cd43573088ef2cd3c6f01c850c6f6cfc7724fcfb273 tests/sealed_hang/common/snap.c
```
