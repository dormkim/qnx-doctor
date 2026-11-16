#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* ecu: sends one bus frame every 10 ms through busgate. */
int main(void) {
  int g = qd_open("busgate");
  for (int n = 0;; n++) { qd_send(g, n); qd_tick("ecu", n); usleep(10000); }
}
