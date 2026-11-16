#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* admind: admin interface; idle unless an operator connects. */
int main(void) {
  name_attach_t *a = qd_attach("admind"); qd_msg_t m;
  for (;;) { int rcvid = qd_receive(a->chid, &m); if (rcvid > 0) MsgReply(rcvid, EOK, NULL, 0); }
}
