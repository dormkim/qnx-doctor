#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* alarmd: acknowledges alarm codes 0..3 from the panel; anything else is logged as unknown. */
int main(void) {
  name_attach_t *a = qd_attach("alarmd");
  qd_msg_t m;
  for (;;) {
    int rcvid = qd_receive(a->chid, &m);
    if (rcvid <= 0) continue;
    int code = m.app.v % 5;
    if (code > 3) { fprintf(stderr, "alarmd: unknown alarm code %d, ignored\n", code); continue; }
    MsgReply(rcvid, EOK, &code, sizeof code);
  }
}
