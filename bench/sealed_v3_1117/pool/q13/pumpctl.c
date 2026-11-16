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

/* pumpctl: sets the valve level every 100 ms and handles slow-down requests between commands. */
static int speed = 100;
static int slow_down(int v) { speed += v; return speed; }
int main(void) {
  name_attach_t *a = qd_attach("pumpctl");
  int valve = qd_open("valve");
  for (int n = 0;; n++) {
    qd_send(valve, n % 5);
    qd_tick("pumpctl", n);
    serve_for(a->chid, 20000000ULL, slow_down);
    usleep(80000);
  }
}
