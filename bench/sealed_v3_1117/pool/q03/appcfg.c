#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* appcfg: reads one key every 50 ms. */
int main(void) {
  int c = qd_open("cfgd");
  for (int n = 0;; n++) { qd_send(c, n); qd_tick("appcfg", n); usleep(50000); }
}
