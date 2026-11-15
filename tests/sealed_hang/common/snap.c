/* snap: take the pidin snapshot at the highest priority, so CPU hogs in a scenario cannot starve the observer. */
#include <stdio.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/neutrino.h>
int main(void) { pthread_setschedprio(pthread_self(), 63); execlp("pidin", "pidin", (char *)NULL); perror("pidin"); return 1; }
