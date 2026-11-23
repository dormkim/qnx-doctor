/* logger <me> <batchd>: writes one log line per step through batchd. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    if (qd_send(coid, n) < 0) perror("log");
    qd_tick(me, n);
  }
}
