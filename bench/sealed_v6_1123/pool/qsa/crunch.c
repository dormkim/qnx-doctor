/* crunch <me>: offline statistics over the trip log. Low priority (6), runs whenever the CPU is free. */
#include "../common/qd.h"
static volatile double s;
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 6);
  sleep(1);
  qd_tick(me, 0);
  for (double x = 1.0;; x += 1.0) s += 1.0 / (x * x);
}
