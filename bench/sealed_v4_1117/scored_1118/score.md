| arm | kind found | deadlock | priority chain | missing reply | multi | healthy | unknown | false alarm | first try fixed | fixed incl. retries (same structure) | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 12/24 | 2/4 | 0/5 | 3/3 | 2/2 | 0/5 | 5/5 | 0/5 | - | - | - | - | 0 | - |
| ai | 12/24 | 2/4 | 0/5 | 3/3 | 2/2 | 0/5 | 5/5 | 0/5 | 5/19 | 5/19 | 0 | 5/19 | 0 | 0 |
| naive | 13/24 | 4/4 | 4/5 | 3/3 | 2/2 | 0/5 | 0/5 | 0/5 | 4/19 | 4/19 | 0 | 4/19 | 0 | 0 |
| naive_x2 | 11/24 | 4/4 | 3/5 | 3/3 | 1/2 | 0/5 | 0/5 | 0/5 | 5/19 | 5/19 | 0 | 5/19 | 0 | 0 |

| axis | n | code kind found | ai kind found | naive kind found | naive_x2 kind found | ai fixed | naive fixed | naive_x2 fixed |
|---|---|---|---|---|---|---|---|---|
| NANOSLEEP read as a hang | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| PRIO_NONE vs PRIO_INHERIT | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| RECEIVE state read as a deadlock | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| RECEIVE state read as blocked | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| RECEIVE-with-timeout read as blocked | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| REPLY vs SEND in a 2-server cycle | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| TimerTimeout used correctly | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| an idle worker read as stuck | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| bug vs missing external data | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| bug vs missing external stimulus | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| call-back during handling | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| cause is not in the provided source | 2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| cycle length 3 not 2 | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| fixed-priority channel breaks inheritance | 1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| idle tail stage | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| inheritance broken mid-chain | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| live producer masks the stuck consumer | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| lock-order inversion | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| long REPLY chain | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| looks like a hang but burns CPU | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| low holder preempted by a mid hog | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| misleading QD-CULPRIT comment | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| no message passing involved | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| no predicate loop | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| one REPLY-starved, one RUNNING spinner | 1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| one pair blocks on SEND, one client on REPLY | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| one process, one thread | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| priority inheritance vs none | 1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| priority starvation | 1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| priority starvation vs missing reply | 1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| protocol expects 2 messages, client sends 1 | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| pulse arrives every 400ms | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| rcvid bookkeeping | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| reply lost vs reply delayed | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| reply missing vs server starved | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 |
| resembles the D01 pingpong send-deadlock | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| round-robin every 300ms | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| self-send with no receiver | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| signal before wait | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| timeout armed on the wrong state | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| timeout present but on the wrong state | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| timeout present but value far too large | 1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| two locks, opposite order | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| two unrelated faults | 1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| two unrelated faults in one capture | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| unit/overflow mistake | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| which code path replies | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 |
| who holds the lock vs who hogs the CPU | 1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 |

### Literal outputs on «unknown» labels
| id | code | ai | naive | naive_x2 |
|---|---|---|---|---|
| D04 | unknown (unknown (spinning): not a message-passing hang: 204820(spin_flag) is running on ) | unknown (unknown (spinning): not a message-passing hang: 204820(spin_flag) is running on ) | none (d004a is a single process that does no message passing. After its 3 TICKs it bus) | none (d004a printed its 3 TICKs and then busy-waits on a flag that nothing sets. It ne) |
| D09 | unknown (unknown (no_info): not enough information: loop stopped, but no wait cycle, prio) | unknown (unknown (no_info): not enough information: loop stopped, but no wait cycle, prio) | none (d009a is a lone server that sits RECEIVE-blocked in MsgReceive on its own channe) | none (d009a is a lone server, RECEIVE-blocked on its own channel. No process ever send) |
| D14 | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | missing_reply (Lost wakeup, not a message hang. The producer (d014a) signals the condvar once, ) | none (No message-passing hang: the program sends no messages. d014a ticks steadily. d0) |
| D18 | unknown (unknown (no_info): not enough information: loop stopped, but no wait cycle, prio) | unknown (unknown (no_info): not enough information: loop stopped, but no wait cycle, prio) | none (d018a is the only process. It attaches its name, prints TICK 0 and then sits REC) | none (d018a is a server with no clients. It ticks once, then sits receive-blocked on i) |
| D24 | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | none (d024a does no message passing at all. It only calls nanosleep for a very long ti) | none (d024a is not hung on a message. It is in a deliberately long nanosleep (3600*100) |
