/* stat <me>: prints the sequencer's current step every 200 ms for the test log. */
#include <fcntl.h>
#include <semaphore.h>
#include <sys/mman.h>
#include "../common/qd.h"

struct ctl { sem_t go; volatile int step; };

int main(int argc, char **argv) {
  const char *me = argv[1];
  int fd;
  usleep(300000);                                 /* sequencer sets the block up first */
  while ((fd = shm_open("/seqr_ctl", O_RDONLY, 0)) == -1) usleep(50000);
  struct ctl *c;
  while ((c = mmap(NULL, sizeof *c, PROT_READ, MAP_SHARED, fd, 0)) == MAP_FAILED) usleep(50000);
  for (int n = 0;; n++) {
    int s = c->step;
    (void)s;
    qd_tick(me, n);
    usleep(200000);
  }
}
