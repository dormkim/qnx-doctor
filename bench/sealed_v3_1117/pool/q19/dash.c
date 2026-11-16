#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* dash: dashboard; waits for each event. */
int main(void) {
  int e = qd_open("evbus");
  for (int n = 0;; n++) { qd_send(e, n); qd_tick("dash", n); }
}
