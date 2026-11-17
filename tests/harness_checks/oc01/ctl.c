#include "../common/qd.h"
int main(void) {
  int pid = 0, chid = 0;
  for (int i = 0; i < 100; i++) {
    FILE *f = fopen("/tmp/ocslow.id", "r");
    if (f && fscanf(f, "%d %d", &pid, &chid) == 2) { fclose(f); break; }
    if (f) fclose(f);
    usleep(50000);
  }
  int coid = ConnectAttach(0, pid, chid, _NTO_SIDE_CHANNEL, 0);
  pthread_setschedprio(pthread_self(), 30);
  for (int n = 0;; n++) { if (qd_send(coid, n) != -1) qd_tick("ctl", n); usleep(20000); }
}
