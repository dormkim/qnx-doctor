# Id shuffle (answers only)

Ids are 30 random 3-character strings (letters without i/l/o, plus digits 2-9). They were drawn with Python
`random.Random(112301)`, and the same generator then shuffled the 30 mix rows onto the sorted ids. The ids carry no
meaning. Role names are `<id>` + a short developer-style tag.

| row | id(s) | mix row |
|---|---|---|
| r01 | cnu, zte | deadlock: ring of sends, TICK before first send |
| r02 | kp6, p5u | missing_reply after a few rounds, one code path |
| r03 | tzy, u7z | deadlock: two mutexes, opposite order |
| r04 | vej, c3n | priority_chain: mutex without inheritance + middle thread |
| r05 | ya8 | healthy: long mutex hold by design |
| r06 | kk5 | deadlock: send to own-process channel, no receiver |
| r07 | kts | healthy: send to own-process channel, other thread replies |
| r08 | euf (load above server), qsa (load below) | healthy: client/server next to a CPU load |
| r09 | e8s, gph | unknown: ticks, then spins |
| r10 | cv4, nrp | deadlock: pool exhaustion |
| r11 | bkr, epe | deadlock: cycle through a relay |
| r12 | g2h (peer), paa (file), quy (external signal) | unknown, info_insufficient |
| r13 | mqj (slow reply), su9 (long poll), exw (timer-driven batch) | healthy: looks stuck |
| r14 | qgj, grp, f82 | priority_chain: qd_fixed_chan server + middle load |
| r15 | g6b, k74 | missing_reply, plain |
