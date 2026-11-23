/* app <me> <cfgd>: reads one setting per cycle. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) perror("setting");
    qd_tick(me, n);
    usleep(100000);
  }
}
