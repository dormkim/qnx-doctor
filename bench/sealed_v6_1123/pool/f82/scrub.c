/* scrub <me>: RAM ECC scrubber, priority 12. */
#include "../common/qd.h"
static volatile unsigned long w[256];
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 12);
  usleep(1200000);
  qd_tick(me, 0);
  for (unsigned long i = 0;; i++) w[i & 255] ^= i;
}
