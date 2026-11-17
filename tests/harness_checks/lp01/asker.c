#include "../common/qd.h"
int main(void) {
  int coid = qd_open("lplate");
  for (int n = 0;; n++) { if (qd_send(coid, n) != -1) qd_tick("asker", n); }
}
