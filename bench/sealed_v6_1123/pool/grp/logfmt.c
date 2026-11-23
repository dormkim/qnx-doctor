/* logfmt <me>: formats the black-box log, priority 16. Prints a progress line every 200 ms. */
#include <time.h>
#include "../common/qd.h"
static volatile unsigned long chars;
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 16);
  sleep(1);
  struct timespec t0, t;
  for (int n = 0;; n++) {
    clock_gettime(CLOCK_MONOTONIC, &t0);
    do { chars++; clock_gettime(CLOCK_MONOTONIC, &t); }
    while ((t.tv_sec - t0.tv_sec) * 1000 + (t.tv_nsec - t0.tv_nsec) / 1000000 < 200);
    qd_tick(me, n);
  }
}
