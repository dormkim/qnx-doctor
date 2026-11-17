#include "../common/qd.h"
#include <time.h>
#include <signal.h>
int main(void) {
  name_attach_t *a = qd_attach("ttwaiter");
  for (int n = 0;; n++) {
    struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
    uint64_t t = 100000000ULL;
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_RECEIVE, &ev, &t, NULL);
    qd_msg_t m;
    if (MsgReceive(a->chid, &m, sizeof m, NULL) == -1 && errno == ETIMEDOUT) qd_tick("waiter", n);
  }
}
