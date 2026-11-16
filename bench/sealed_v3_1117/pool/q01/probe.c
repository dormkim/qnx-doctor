#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* probe: reports a sample every 50 ms. */
int main(void) {
  int t = qd_open("telemetryd");
  for (int n = 0;; n++) { qd_send(t, n); qd_tick("probe", n); usleep(50000); }
}
