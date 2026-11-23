/* fc <me> <imud>: flight control, priority 32, one attitude sample per 100 ms. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 32);
  int imu = qd_open_fixed(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(imu, n) < 0) perror("attitude");
    qd_tick(me, n);
    usleep(100000);
  }
}
