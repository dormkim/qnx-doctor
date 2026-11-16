#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* player: audio loop at priority 30, one block per 20 ms. */
int main(void) {
  setprio(0, 30);
  int c = qd_open("codecd");
  for (int n = 0;; n++) { qd_send(c, n); qd_tick("player", n); usleep(20000); }
}
