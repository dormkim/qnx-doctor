| arm | kind found | deadlock | priority chain | missing reply | multi | healthy | unknown | false alarm | first try fixed | fixed incl. retries (same structure) | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 10/12 | 2/2 | 4/4 | 2/2 | 0/0 | 0/2 | 2/2 | 1/2 | - | - | - | - | 0 | - |
| ai | 10/12 | 2/2 | 4/4 | 2/2 | 0/0 | 0/2 | 2/2 | 1/2 | 4/10 | 4/10 | 0 | 4/10 | 0 | 0 |
| naive | 8/12 | 2/2 | 4/4 | 2/2 | 0/0 | 0/2 | 0/2 | 0/2 | 4/10 | 4/10 | 0 | 4/10 | 0 | 0 |
| naive_x2 | 8/12 | 2/2 | 4/4 | 2/2 | 0/0 | 0/2 | 0/2 | 0/2 | 4/10 | 4/10 | 0 | 4/10 | 0 | 0 |

| axis | n | code kind found | ai kind found | naive kind found | naive_x2 kind found | ai fixed | naive fixed | naive_x2 fixed |
|---|---|---|---|---|---|---|---|---|
| fixed-priority channel breaks inheritance | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 | 3/4 | 3/4 |
| healthy vs a hang | 2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| message-passing hang vs out-of-scope hang | 2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| missing reply vs priority starvation | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 | 1/2 | 1/2 |
| priority starvation vs missing reply | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 | 3/4 | 3/4 |
| send cycle vs priority starvation | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/2 |

### Literal outputs on «unknown» labels
| id | code | ai | naive | naive_x2 |
|---|---|---|---|---|
| E11 | unknown (unknown (spinning): not a message-passing hang: 204820(spin) is running on the C) | unknown (unknown (spinning): not a message-passing hang: 204820(spin) is running on the C) | none (The single process d0e11a sends and receives no messages. It printed its 3 TICKs) | none (Single process with no message passing: it prints 3 TICKs, then busy-spins on a ) |
| E12 | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | unknown (unknown (blocked_other): not a message-passing hang: loop stopped while blocked ) | none (No message-passing hang: d0e12a sends and receives no messages. It printed its 3) | none (Single process with no message passing. After 3 TICKs it blocks in sem_wait on a) |
