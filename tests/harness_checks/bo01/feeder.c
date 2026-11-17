#include "../common/qd.h"
#include <semaphore.h>
static sem_t go;   /* initialised to 0, never posted */
int main(void) {   /* a few rounds, then waits on a semaphore nobody posts: stopped outside message passing */
  sem_init(&go, 0, 0);
  for (int n = 0;; n++) {
    if (n == 3) sem_wait(&go);
    qd_tick("feeder", n); usleep(100000);
  }
}
