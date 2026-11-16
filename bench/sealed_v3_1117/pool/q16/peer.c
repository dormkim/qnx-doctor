#include "../common/qd.h"
#include <time.h>
#include <signal.h>

static uint64_t now_ns(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}

/* Answer whatever arrives on chid for up to ns nanoseconds, then return. */
static void serve_for(int chid, uint64_t ns, int (*answer)(int)) {
  uint64_t end = now_ns() + ns;
  for (;;) {
    uint64_t t = now_ns();
    if (t >= end) return;
    uint64_t left = end - t; struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, &ev, &left, NULL);
    qd_msg_t m; int rcvid = MsgReceive(chid, &m, sizeof m, NULL);
    if (rcvid == -1) { if (errno == ETIMEDOUT) return; continue; }
    if (rcvid == 0) { if (m.pulse.code == _PULSE_CODE_DISCONNECT) ConnectDetach(m.pulse.scoid); continue; }
    if (m.type == _IO_CONNECT) { MsgReply(rcvid, EOK, NULL, 0); continue; }
    if (m.type > _IO_BASE && m.type <= _IO_MAX) { MsgError(rcvid, ENOSYS); continue; }
    int r = answer(m.app.v); MsgReply(rcvid, EOK, &r, sizeof r);
  }
}

/* peer <me> <other> <startup_ms>: two peers that each push a sample to the other.
 * Every push carries a 200 ms send+reply timeout; on a timeout the peer serves the other side for a while. */
static int answer(int v) { return v + 1; }
int main(int argc, char **argv) {
  if (argc < 4) return 2;
  const char *me = argv[1];
  name_attach_t *a = qd_attach(me);
  serve_for(a->chid, (uint64_t)atoi(argv[3]) * 1000000ULL, answer);
  int o = qd_open(argv[2]);
  srand(getpid());
  for (int n = 0;;) {
    struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
    uint64_t t = (150 + rand() % 100) * 1000000ULL;
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY, &ev, &t, NULL);
    if (qd_send(o, n) != -1) { qd_tick(me, n); n++; }
    serve_for(a->chid, (uint64_t)(50 + rand() % 50) * 1000000ULL, answer);
  }
}
