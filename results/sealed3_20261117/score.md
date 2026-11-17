Excluded (unmodified run did not match «expect»): 5
- q02: unmodified run: the loop expected to stop had printed 35 TICKs at the check.sh snapshot, and a second count could not be taken (the second observer, started before the scenario and woken by a timer, never finished: its reads of /tmp on disk were starved, tried twice). The harness the arms use sees only that first count, so «stops» cannot be confirmed; label not edited.
- q06: unmodified run: the loop expected to stop had printed 37 TICKs at the check.sh snapshot, and a second count could not be taken (the second observer, started before the scenario and woken by a timer, never finished: its reads of /tmp on disk were starved, tried twice). The harness the arms use sees only that first count, so «stops» cannot be confirmed; label not edited.
- q09: unmodified run: the loop expected to stop had printed 36 TICKs at the check.sh snapshot, and a second count could not be taken (the second observer, started before the scenario and woken by a timer, never finished: its reads of /tmp on disk were starved, tried twice). The harness the arms use sees only that first count, so «stops» cannot be confirmed; label not edited.
- q16: unmodified run: east and west, expected to keep ticking, printed 0 TICKs at the snapshot and still 0 a moment later; same on a second run (early timer). Label not edited.
- q21: unmodified run: the loop expected to stop had printed 15 TICKs at the check.sh snapshot, and a second count could not be taken (the second observer, started before the scenario and woken by a timer, never finished: its reads of /tmp on disk were starved, tried twice). The harness the arms use sees only that first count, so «stops» cannot be confirmed; label not edited.

| arm | kind found | deadlock | priority chain | missing reply | healthy | unknown | false alarm | first try fixed | fixed incl. retries (same structure) | shortcut rejected | liveness-only would accept | false fix | fixed on unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 13/16 | 4/5 | 0/0 | 3/3 | 3/4 | 3/4 | 1/4 | - | - | - | - | 0 | - |
| ai | 13/16 | 4/5 | 0/0 | 3/3 | 3/4 | 3/4 | 1/4 | 3/8 | 3/8 | 0 | 3/8 | 0 | 0 |
| naive | 12/16 | 5/5 | 0/0 | 3/3 | 4/4 | 0/4 | 0/4 | 2/8 | 2/8 | 0 | 2/8 | 0 | 2 |
| naive_x2 | 11/16 | 4/5 | 0/0 | 3/3 | 4/4 | 0/4 | 0/4 | 3/8 | 3/8 | 1 | 4/8 | 0 | 3 |

| axis | n | code kind found | ai kind found | naive kind found | naive_x2 kind found | ai fixed | naive fixed | naive_x2 fixed |
|---|---|---|---|---|---|---|---|---|
| config_error | 1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| cpu_spin | 1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/0 | 0/0 | 0/0 |
| deferred_reply | 3 | 2/3 | 2/3 | 3/3 | 3/3 | 1/2 | 0/2 | 1/2 |
| external_dependency | 2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| latent_after_n_rounds | 2 | 2/2 | 2/2 | 2/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| looks_like_missing_reply | 2 | 1/2 | 1/2 | 2/2 | 2/2 | 0/0 | 0/0 | 0/0 |
| looks_like_priority_chain | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 |
| misleading_comment | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| misleading_log | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/2 | 0/2 | 0/2 |
| multi_cause | 1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| near_miss | 4 | 3/4 | 3/4 | 4/4 | 4/4 | 0/0 | 0/0 | 0/0 |
| not_enough_information | 2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| outside_vocabulary | 2 | 1/2 | 1/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 |
| partial_stop | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 |
| pulse_callback | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 |
| runtime_wiring | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| send_hierarchy | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| timeout_misuse | 1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| timer_pulse | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 |
| timing_race | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |

### Literal outputs on «unknown» labels
| id | code | ai | naive | naive_x2 |
|---|---|---|---|---|
| q01 | none (loop not running but no wait cycle or chain found) | none (loop not running but no wait cycle or chain found) | none (This is not a message-passing hang but a name mismatch, so none of the hang cate) | missing_reply (The probe never gets an answer because the names do not match: telemetryd regist) |
| q11 | none (no hang found) | none (no hang found) | missing_reply (uplink logged 6 TICKs (n=0..5) and then hung on its 7th send (n=6), where len is) | missing_reply (When uplink sends an odd length (7 on every 7th message), parsed's counting loop) |
| q12 | none (loop not running but no wait cycle or chain found) | none (loop not running but no wait cycle or chain found) | missing_reply (After busgate receives ecu's first message, it calls sigwaitinfo() for SIGUSR2 b) | missing_reply (busgate receives ecu's first message, then blocks in sigwaitinfo for a SIGUSR2 t) |
| q17 | none (loop not running but no wait cycle or chain found) | none (loop not running but no wait cycle or chain found) | missing_reply (calsrv attaches its name and then blocks in sem_wait on /calready, which nothing) | missing_reply (calsrv attaches its name and then blocks in sem_wait on /calready, which no proc) |

### «Fixed» on info_insufficient labels (read by a human)
- naive q12
- naive_x2 q12
- naive q17
- naive_x2 q17
