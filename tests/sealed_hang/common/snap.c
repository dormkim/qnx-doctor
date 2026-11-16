/* snap: the observer. check.sh starts it BEFORE the scenario, so it is already in memory, and it waits for SIGUSR1
 * (sent with the shell builtin `kill`, so nothing has to be loaded at that moment). Then, at priority 63, it counts
 * the TICK lines of every /tmp/d0*.log and prints a pidin snapshot (pidin runs from /proc/boot, i.e. RAM).
 *
 * Why (harness fix, 2026-11-16, found on dev seeds only): /var and /tmp live on the disk image, served by devb-eide
 * whose threads run at priority 21. A scenario hog at priority 22 on both CPUs starves the disk driver, so an
 * observer loaded from disk AFTER the scenario only ran once the hog had finished — it saw a system that had already
 * recovered (dev seeds 1003 and 1017: hog missing from the snapshot, client TICKs counted after the hog ended).
 * Labels and scenario sources are unchanged.
 *
 * After the TICK counts it prints `pidin arg` (pid -> command line, so a process can be matched across two boots by
 * what was started, not by its pid) and the message records of qd_trace.c (/dev/shmem/qdm.<pid>). Added
 * 2026-11-16 for the «same message structure» check; the pidin snapshot itself is unchanged. */
#include <dirent.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int ticks(const char *path) {
  FILE *f = fopen(path, "r");
  char line[256];
  int n = 0;
  if (!f) return -1;
  while (fgets(line, sizeof line, f)) n += strstr(line, "TICK") != NULL;
  fclose(f);
  return n;
}

int main(void) {
  sigset_t s;
  sigemptyset(&s); sigaddset(&s, SIGUSR1);
  sigprocmask(SIG_BLOCK, &s, NULL);
  pthread_setschedprio(pthread_self(), 63);
  int sig = 0;
  sigwait(&s, &sig);
  char out[4096], path[300];
  size_t n = 0;
  DIR *d = opendir("/tmp");
  struct dirent *e;
  while (d && (e = readdir(d)) && n < sizeof out - 400) {
    size_t l = strlen(e->d_name);
    if (strncmp(e->d_name, "d0", 2) || l < 6 || strcmp(e->d_name + l - 4, ".log")) continue;
    snprintf(path, sizeof path, "/tmp/%s", e->d_name);
    n += snprintf(out + n, sizeof out - n, "%s %d\n", path, ticks(path));
  }
  if (d) closedir(d);
  puts("=== PIDIN ==="); fflush(stdout);
  pid_t p = fork();
  if (p == 0) { execl("/proc/boot/pidin", "pidin", (char *)NULL); execlp("pidin", "pidin", (char *)NULL); _exit(127); }
  if (p > 0) waitpid(p, NULL, 0);
  printf("=== TICKS ===\n%s", out);
  puts("=== ARGS ==="); fflush(stdout);
  p = fork();
  if (p == 0) { execl("/proc/boot/pidin", "pidin", "arg", (char *)NULL); execlp("pidin", "pidin", "arg", (char *)NULL); _exit(127); }
  if (p > 0) waitpid(p, NULL, 0);
  puts("=== MSGS ===");
  d = opendir("/dev/shmem");
  while (d && (e = readdir(d))) {
    if (strncmp(e->d_name, "qdm.", 4)) continue;
    snprintf(path, sizeof path, "/dev/shmem/%s", e->d_name);
    FILE *f = fopen(path, "r");
    char line[128];
    while (f && fgets(line, sizeof line, f)) printf("%s %s", e->d_name + 4, line);
    if (f) fclose(f);
  }
  if (d) closedir(d);
  puts("=== END ==="); fflush(stdout);
  return 0;
}
