#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* panel: raises one alarm code every 100 ms and waits for alarmd's acknowledgement. */
int main(void) {
  int al = qd_open("alarmd");
  for (int n = 0;; n++) { qd_send(al, n); qd_tick("panel", n); usleep(100000); }
}
