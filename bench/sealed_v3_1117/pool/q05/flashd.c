#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* flashd: writes a record to flash; each write takes about 0.9 s. */
int main(void) {
  name_attach_t *a = qd_attach("flashd");
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    usleep(900000);
    MsgReply(rcvid, EOK, NULL, 0);
  }
}
