#include "../common/qd.h"
#include <time.h>
#include <signal.h>

static uint64_t now_ns(void) {
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
}

/* routemap: computes a route. It needs navcore's current position and fetches it with a synchronous
 * query. Every send carries a 300 ms timeout and is retried, so routemap cannot hang on navcore. */
static int ask_with_timeout(int coid, int v) {
  struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
  uint64_t t = 300000000ULL;
  TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND, &ev, &t, NULL);
  return qd_send(coid, v);
}
int main(void) {
  name_attach_t *a = qd_attach("routemap");
  int nav = qd_open("navcore");
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    int pos, tries = 0;
    while ((pos = ask_with_timeout(nav, -1)) == -1)
      if (++tries % 10 == 0) fprintf(stderr, "routemap: position query timed out %d times, retrying\n", tries);
    int route = m.app.v + pos;
    MsgReply(rcvid, EOK, &route, sizeof route);
  }
}
