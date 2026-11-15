/* hi <cmd...>: run the check at priority 50, so a scenario's CPU hogs (priority 20) cannot delay the observer's
 * own sleep/snapshot. Harness only — added before the first run of the set; labels unchanged. */
#include <stdio.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/neutrino.h>
int main(int argc, char **argv) { if (argc < 2) return 2; pthread_setschedprio(pthread_self(), 50); execvp(argv[1], argv + 1); perror(argv[1]); return 1; }
