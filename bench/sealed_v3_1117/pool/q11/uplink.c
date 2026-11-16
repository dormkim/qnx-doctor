#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* uplink: sends a frame every 20 ms; every 7th frame carries a 7-byte trailer. */
int main(void) {
  int p = qd_open("parsed");
  for (int n = 0;; n++) {
    int len = (n % 7 == 6) ? 7 : 4 * (n % 5 + 1);
    qd_send(p, len); qd_tick("uplink", n); usleep(20000);
  }
}
