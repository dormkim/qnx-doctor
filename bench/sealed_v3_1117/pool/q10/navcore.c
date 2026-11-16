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

/* navcore: asks routemap for a route every 200 ms and answers position queries in between.
 * Route requests carry a 300 ms timeout, so a stuck routemap cannot freeze navigation. */
static int pos;
static int answer_pos(int v) { (void)v; return pos; }
int main(void) {
  name_attach_t *a = qd_attach("navcore");
  serve_for(a->chid, 1500000000ULL, answer_pos);     /* start-up: let routemap connect */
  int map = qd_open("routemap");
  for (int n = 0;; n++) {
    struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
    uint64_t t = 300000000ULL;
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND, &ev, &t, NULL);
    if (qd_send(map, n) != -1) qd_tick("navcore", n);
    else { printf("navcore: route request timed out\n"); fflush(stdout); }
    pos++;
    serve_for(a->chid, 50000000ULL, answer_pos);
    usleep(150000);
  }
}
