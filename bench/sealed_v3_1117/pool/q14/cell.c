#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* cell <me>: takes the tool, uses it for 30 ms, gives it back. */
int main(int argc, char **argv) {
  if (argc < 2) return 2;
  int l = qd_open("lockd");
  for (int n = 0;; n++) {
    qd_send(l, 1);
    usleep(30000);
    qd_send(l, 0);
    qd_tick(argv[1], n);
    usleep(5000 + (getpid() % 7) * 1000);
  }
}
