#include "../common/qd.h"
#include <time.h>
#include <signal.h>

#include <semaphore.h>
#include <fcntl.h>
/* calsrv: serves calibrated torque values. It starts serving only after the end-of-line calibration
 * tool (run by the technician on the line) posts the named semaphore /calready. */
int main(void) {
  name_attach_t *a = qd_attach("calsrv");
  sem_t *ready = sem_open("/calready", O_CREAT, 0644, 0);
  if (ready == SEM_FAILED) { perror("sem_open"); return 1; }
  sem_wait(ready);
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    int t = m.app.v * 3;
    MsgReply(rcvid, EOK, &t, sizeof t);
  }
}
