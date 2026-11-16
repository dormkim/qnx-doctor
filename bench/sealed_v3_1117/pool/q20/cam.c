#include "../common/qd.h"
#include <time.h>
#include <signal.h>

/* cam: pushes one frame every 100 ms to framestore. */
int main(void) {
  int st = qd_open("framestore");
  printf("cam: WARNING storage latency high on this board, frames may queue\n"); fflush(stdout);
  for (int n = 0;; n++) {
    qd_send(st, n);
    qd_tick("cam", n);
    if (n % 3 == 2) { printf("cam: storage slow, %d frames in flight\n", n + 1); fflush(stdout); }
    usleep(100000);
  }
}
