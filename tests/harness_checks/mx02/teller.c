#include "../common/qd.h"
int main(void) {
  int coid = qd_open("mxdesk");
  for (int n = 0;; n++) { qd_tick("teller", n); qd_send(coid, n); usleep(50000); }
}
