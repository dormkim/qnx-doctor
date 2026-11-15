/* snap: take the pidin snapshot at the highest priority, so CPU hogs in a scenario cannot starve the observer. */
#include <stdio.h>
#include <unistd.h>
#include <sys/neutrino.h>
int main(void) { setprio(0, 63); execlp("pidin", "pidin", (char *)NULL); perror("pidin"); return 1; }
