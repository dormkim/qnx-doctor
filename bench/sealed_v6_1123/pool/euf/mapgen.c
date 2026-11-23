/* mapgen <me>: rebuilds the routing tiles in the background. CPU-bound by nature; runs at 15. */
#include "../common/qd.h"
static volatile unsigned long acc;
int main(int argc, char **argv) {
  const char *me = argv[1];
  setprio(0, 15);
  sleep(1);                                       /* let the stack come up first */
  qd_tick(me, 0);
  for (unsigned long i = 0;; i++) acc += i * 2654435761u;   /* tile hashing */
}
