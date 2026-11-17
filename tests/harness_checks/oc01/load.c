#include "../common/qd.h"
static void *spin(void *x) { (void)x; pthread_setschedprio(pthread_self(), 22); for (;;) {} return NULL; }
int main(void) {   /* two CPU-bound threads above the disk driver (21) on both CPUs */
  pthread_t t; pthread_create(&t, NULL, spin, NULL);
  spin(NULL);
}
