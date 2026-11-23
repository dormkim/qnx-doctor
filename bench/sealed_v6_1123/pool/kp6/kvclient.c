/* kvclient <me> <store> <w|r>: writer stores a counter, reader polls it. */
#include "../common/qd.h"
int main(int argc, char **argv) {
  const char *me = argv[1];
  int writer = argv[3][0] == 'w';
  int coid = qd_open(argv[2]);
  for (int n = 0;; n++) {
    int r = qd_send(coid, writer ? n : -1);
    if (r < 0) perror("kv");
    qd_tick(me, n);
    usleep(writer ? 80000 : 100000);
  }
}
