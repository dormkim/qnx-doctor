/* hmi <me> <pwrmgr>: sets the backlight rail every cycle; every 7th cycle it also tells pwrmgr it is alive. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    int v = (n % 7 == 6) ? -1 : 40 + n % 20;
    qd_send(coid, v);
    qd_tick(me, n);
    usleep(100000);
  }
}
