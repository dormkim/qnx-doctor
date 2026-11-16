#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* client <me> <server>: one request every 5 ms. */
int main(int argc, char **argv) {
  if (argc < 3) return 2;
  int s = qd_open(argv[2]);
  for (int n = 0;; n++) { qd_send(s, n); qd_tick(argv[1], n); usleep(5000); }
}
