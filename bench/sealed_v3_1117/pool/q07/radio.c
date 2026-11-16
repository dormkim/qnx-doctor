#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* radio: transmits once per slot. */
int main(void) {
  int s = qd_open("slotd");
  for (int n = 0;; n++) { qd_send(s, n); qd_tick("radio", n); }
}
