#include "../common/qd.h"
#include <fcntl.h>
int main(void) {   /* fixed-priority channel: the server stays at 5 whatever the client's priority */
  int chid = ChannelCreate(_NTO_CHF_FIXED_PRIORITY);
  char b[32]; int n = snprintf(b, sizeof b, "%d %d\n", getpid(), chid);
  int fd = open("/tmp/ocslow.id", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  (void)!write(fd, b, n); close(fd);
  pthread_setschedprio(pthread_self(), 5);
  for (;;) {
    qd_msg_t m;
    int rcvid = MsgReceive(chid, &m, sizeof m, NULL);
    if (rcvid <= 0) continue;
    for (volatile int i = 0; i < 200000; i++) {}
    MsgReply(rcvid, EOK, NULL, 0);
  }
}
