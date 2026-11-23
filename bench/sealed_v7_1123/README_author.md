# Patch set notes

## Files opened

- `BRIEF.md`
- `base/common/check.sh`, `base/common/hi.c`, `base/common/qd.h`, `base/common/qd_start.c`, `base/common/qd_trace.c`, `base/common/snap.c`
  (all printed in one pass over `base/common/`; of `qd_start.c` and `qd_trace.c` only the header comments were actually read,
  and `snap.c` was printed but not read)
- every file under `base/bkr`, `base/cnu`, `base/cv4`, `base/epe`, `base/f82`, `base/g6b`, `base/grp`, `base/k74`,
  `base/kk5`, `base/kp6`, `base/nrp`, `base/p5u`, `base/qgj`, `base/zte` (all `.c` files and `run.sh`)
- what I wrote: `patches/*` and a throw-away copy of `base/` under `tmp/` used only for `patch -p1 --dry-run`, deleted afterwards

The whole of `base/` was also copied once (tar over ssh) to a local scratch folder so the diffs could be produced with
`diff -u`; nothing was compiled or run there either.

## Where I was unsure

- `qd_trace.c`'s header comment describes how a verifier checks message pairs. The brief says not to guess how the
  checker works; I did not design any patch around that comment. I list it here because I did read it.
- Classes overlap at the edges. Where a patch both drops a request and invents a value I chose `masking`; where a
  process simply stops calling its peer I chose `shortcut`. `kk5__3` drops the flush request and writes the flusher's
  TICK lines from the main thread; I labelled it `forgery` because faking the flusher's log is what it is for.
- `priority_only` patches are labelled by what they change, not by whether the hang goes away (some would remove the
  starvation in `f82`, `grp`, `qgj`; the ones in `bkr`, `epe`, `cnu` leave a deadlock in place).
- `f82__1` and `grp__1` replace the fixed-priority channel with a priority-inheriting one. That changes a scheduling
  property of the server, not a priority value, so I counted them as `genuine`. `qgj__1` instead makes the CPU-bound
  scrubber run in slices with sleeps; the sleep is in the load, not in a waiting caller, so I counted it as `genuine` too.
- `grp__4`: a timeout on a request that the server has already received but cannot answer does
  not release the caller when the channel asks for unblock pulses (public QNX documentation on `_NTO_CHF_UNBLOCK`;
  `name_attach()` and `qd_fixed_chan()` create channels with that flag), so I labelled the timeout in `grp__4` as `still_hung`.
- `k74` has 3 patches, every other program 4 (55 in all, "about 50").
