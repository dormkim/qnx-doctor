/* seqr <me>: test sequencer. Runs the self-test steps, then each epoch waits for the supervisor's go
 * (process-shared semaphore in /seqr_ctl) before driving the next step. */
#include <fcntl.h>
#include <semaphore.h>
#include <sys/mman.h>
#include "../common/qd.h"

struct ctl { sem_t go; volatile int step; };

int main(int argc, char **argv) {
  const char *me = argv[1];
  int created = 1;
  int fd = shm_open("/seqr_ctl", O_RDWR | O_CREAT | O_EXCL, 0666);
  if (fd == -1) { created = 0; fd = shm_open("/seqr_ctl", O_RDWR, 0666); }
  if (fd == -1) { perror("shm_open"); return 1; }
  if (created && ftruncate(fd, sizeof(struct ctl)) == -1) { perror("ftruncate"); return 1; }
  struct ctl *c = mmap(NULL, sizeof *c, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (c == MAP_FAILED) { perror("mmap"); return 1; }
  if (created) sem_init(&c->go, 1, 0);

  for (int n = 0;; n++) {
    if (n >= 5) sem_wait(&c->go);                 /* supervisor releases the epoch */
    c->step = n;
    qd_tick(me, n);
    usleep(200000);
  }
}
