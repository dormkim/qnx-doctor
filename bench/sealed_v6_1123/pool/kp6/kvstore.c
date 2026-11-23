/* kvstore <me>: small key/value store.
 * Reads (v < 0) are answered at once. A write (v >= 0) is acknowledged by the commit pulse (every 50 ms) once
 * the journal holds it. Every few commits the journal is compacted first. */
#include <time.h>
#include "../common/qd.h"

#define COMMIT_CODE (_PULSE_CODE_MINAVAIL + 1)
#define JOURNAL_MAX 6

static int journal[64], jlen;
static void compact(void) { memmove(journal, journal + jlen / 2, (jlen - jlen / 2) * sizeof journal[0]); jlen -= jlen / 2; }

int main(int argc, char **argv) {
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);

  int self = ConnectAttach(0, 0, a->chid, _NTO_SIDE_CHANNEL, 0);
  struct sigevent ev; SIGEV_PULSE_INIT(&ev, self, SIGEV_PULSE_PRIO_INHERIT, COMMIT_CODE, 0);
  timer_t tid; timer_create(CLOCK_MONOTONIC, &ev, &tid);
  struct itimerspec its = { { 0, 50000000 }, { 0, 50000000 } };
  timer_settime(tid, 0, &its, NULL);

  int pending_write = 0, value = 0, dirty = 0, n = 0;
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid == 0) {
      if (m.pulse.code != COMMIT_CODE || !pending_write) continue;
      journal[jlen++ & 63] = value;
      if (++dirty >= JOURNAL_MAX) {        /* compaction: the writer is acked by the commit after it */
        compact(); dirty = 0; pending_write = 0;
        continue;
      }
      MsgReply(pending_write, EOK, &value, sizeof value);
      pending_write = 0;
      qd_tick(me, n++);
      continue;
    }
    if (m.app.v >= 0) { value = m.app.v; pending_write = rcvid; continue; }
    MsgReply(rcvid, EOK, &value, sizeof value);      /* read */
    qd_tick(me, n++);
  }
}
