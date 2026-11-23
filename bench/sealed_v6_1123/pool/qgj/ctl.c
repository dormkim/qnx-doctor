/* ctl <me> <adcd>: motor current loop, 10 Hz. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 30);
  int coid = qd_open_fixed(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) perror("adc");
    qd_tick(me, n);
    usleep(100000);
  }
}
