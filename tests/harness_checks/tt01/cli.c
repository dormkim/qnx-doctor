#include "../common/qd.h"
#include <time.h>
#include <signal.h>
int main(void) {
  int pid = 0, chid = 0;
  for (int i = 0; i < 100; i++) {
    FILE *f = fopen("/dev/shmem/ttmute.id", "r");
    if (f && fscanf(f, "%d %d", &pid, &chid) == 2) { fclose(f); break; }
    if (f) fclose(f);
    usleep(50000);
  }
  int coid = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0);
  for (int n = 0;; n++) {
    struct sigevent ev; SIGEV_UNBLOCK_INIT(&ev);
    uint64_t t = 100000000ULL;
    TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND, &ev, &t, NULL);
    if (qd_send(coid, n) == -1 && errno == ETIMEDOUT) qd_tick("cli", n);
  }
}
