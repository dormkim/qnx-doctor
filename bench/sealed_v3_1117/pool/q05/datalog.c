#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* datalog: stores one record per round and complains when flashd is slow. */
int main(void) {
  int f = qd_open("flashd");
  for (int n = 0;; n++) {
    qd_send(f, n);
    printf("datalog: WARN flashd reply slow (>500 ms), possible hang\n");
    qd_tick("datalog", n);
  }
}
