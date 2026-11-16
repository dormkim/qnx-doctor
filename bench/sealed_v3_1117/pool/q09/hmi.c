#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* hmi: the display loop at priority 30; stores one setting per frame. */
int main(void) {
  setprio(0, 30);
  int r = qd_open("cfgrouter");
  for (int n = 0;; n++) { qd_send(r, n); qd_tick("hmi", n); usleep(20000); }
}
