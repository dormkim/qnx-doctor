#include "../common/qd.h"
#include <fcntl.h>
int main(void) {   /* a channel that never receives (no name_attach, so no connect message to answer) */
  int chid = ChannelCreate(0);
  char b[32]; int n = snprintf(b, sizeof b, "%d %d\n", getpid(), chid);
  int fd = open("/dev/shmem/ttmute.id", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  (void)!write(fd, b, n); close(fd);
  for (;;) pause();
}
