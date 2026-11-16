#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* torque: control loop reading one calibrated value every 10 ms. */
int main(void) {
  int c = qd_open("calsrv");
  for (int n = 0;; n++) { qd_send(c, n); qd_tick("torque", n); usleep(10000); }
}
