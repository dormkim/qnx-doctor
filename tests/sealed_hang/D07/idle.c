/* idle worker|feeder: two workers wait for work (RECEIVE-blocked); a feeder sends them pulses now and then. Not a fault. */
#include "../common/qd.h"
static void worker(const char *me) { name_attach_t *a = qd_attach(me); qd_msg_t m; for (int n = 0;; n++) { qd_receive(a->chid, &m); qd_tick(me, n); } }
static void feeder(void) {
  int w1 = qd_open("d07w1"), w2 = qd_open("d07w2");
  for (int n = 0;; n++) { MsgSendPulse(w1, -1, 1, n); MsgSendPulse(w2, -1, 1, n); usleep(300000); }
}
int main(int argc, char **argv) { if (!strcmp(argv[1], "feeder")) feeder(); else worker(argv[1]); return 0; }
