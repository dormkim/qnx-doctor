| arm | kind found | deadlock | priority chain | missing reply | multi | healthy | unknown | false alarm | first try fixed | fixed incl. retries (same structure) | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 22/30 | 6/9 | 3/5 | 4/4 | 0/0 | 4/7 | 5/5 | 3/7 | - | - | - | - | 0 | - |
| ai | 22/30 | 6/9 | 3/5 | 4/4 | 0/0 | 4/7 | 5/5 | 3/7 | 11/18 | 11/18 | 4 | 13/18 | 0 | 0 |
| naive | 26/30 | 7/9 | 3/5 | 4/4 | 0/0 | 7/7 | 5/5 | 0/7 | 12/18 | 12/18 | 2 | 14/18 | 0 | 0 |
| naive_x2 | 25/30 | 6/9 | 3/5 | 4/4 | 0/0 | 7/7 | 5/5 | 0/7 | 12/18 | 14/18 | 2 | 14/18 | 0 | 0 |

| axis | n | code kind found | ai kind found | naive kind found | naive_x2 kind found | ai fixed | naive fixed | naive_x2 fixed |
|---|---|---|---|---|---|---|---|---|
| load_vs_server | 2 | 0/2 | 0/2 | 2/2 | 2/2 | 0/0 | 0/0 | 0/0 |
| mechanism | 30 | 22/30 | 22/30 | 26/30 | 25/30 | 11/18 | 12/18 | 14/18 |
| missing | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/0 | 0/0 | 0/0 |
| processes | 30 | 22/30 | 22/30 | 26/30 | 25/30 | 11/18 | 12/18 | 14/18 |
| shape | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| threads | 30 | 22/30 | 22/30 | 26/30 | 25/30 | 11/18 | 12/18 | 14/18 |
| trap | 27 | 19/27 | 19/27 | 23/27 | 22/27 | 11/18 | 12/18 | 14/18 |

### Literal outputs on «unknown» labels
| id | code | ai | naive | naive_x2 |
|---|---|---|---|---|
| e8s | unknown (unknown (spinning): not a message-passing hang: 204820(parser) is running on the) | unknown (unknown (spinning): not a message-passing hang: 204820(parser) is running on the) | unknown (The parser printed TICK 0-5 and then stopped in a busy CPU loop, not in message ) | unknown (No message passing is involved. At n==6, build_frame writes a field with vlen==0) |
| g2h | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (After 6 requests, cfgd keeps calling name_open("g2hkeys") with usleep in a loop ) | unknown (Each loop stopped after 6 ticks; at 100 ms per send, about 40 were expected in t) |
| gph | unknown (unknown (spinning): not a message-passing hang: 204820(lru) is running on the CP) | unknown (unknown (spinning): not a message-passing hang: 204820(lru) is running on the CP) | unknown (The only loop has stopped, but in a CPU-bound infinite loop, not in message pass) | unknown (Not a message-passing hang. gphlru prints 6 TICKs (n=0..5), then spins in a CPU ) |
| paa | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (After 5 ticks the ctrl thread waits on a condition variable for limits that the ) | unknown (After 5 ticks the ctrl thread waits on a condition variable for limits that the ) |
| quy | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (After 5 ticks seqr blocks in sem_wait on the shared-memory semaphore c->go, and ) | unknown (After 5 ticks seqr blocks in sem_wait on a shared-memory semaphore that no proce) |
