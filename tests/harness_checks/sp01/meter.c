#include "../common/qd.h"
static volatile int cal_ok;      /* nobody ever sets it */
static volatile unsigned long cal_rounds;
int main(void) {   /* stores a few readings, then waits for calibration in a busy loop: spins, never blocks */
  int coid = qd_open("spstore");
  for (int n = 0;; n++) {
    if (n == 5) while (!cal_ok) cal_rounds++;
    qd_send(coid, n); qd_tick("meter", n); usleep(100000);
  }
}
