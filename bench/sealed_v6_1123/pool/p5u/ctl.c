/* ctl <me> <server>: control loop, one conversion request per 100 ms cycle. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) { perror("convert"); usleep(100000); continue; }   /* shed: retry next cycle */
    qd_tick(me, n);
    usleep(100000);
  }
}
