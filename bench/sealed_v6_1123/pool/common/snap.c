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
 * 2026-11-16 for the «same message structure» check; the pidin snapshot itself is unchanged.
 *
 * Nothing is printed until both pidin runs are done (harness fix 2026-11-17, found on dev v2 t54e3fe): pidin writes
 * into RAM files (/dev/shmem) and snap prints them afterwards. Before, the "=== PIDIN ===" line went to the serial
 * console just before pidin looked, which woke the serial driver (devc-ser8250, priority 25). In a scenario with a
 * fixed-priority server at 3-8 and its client at 25-40, that made the observer's own printing the «middle» thread of a
 * priority chain, while the server was busy on a request. Two v2 held-out reruns were judged «chain» that way.
 * The same day: two more pidin snapshots follow a moment later (PIDIN2, PIDIN3); waitgraph.judge counts a chain or a
 * missing reply only if it is in all three. The first snapshot and the TICK counts are taken as before.
 *
 * TICKS2 (2026-11-17, before sealed v4; docs/분석_sealed3_1117.md J1/H2): after PIDIN3 and a short wait the TICK
 * lines are counted again, in the same boot. A state snapshot alone cannot tell a server that answers on every timer
 * pulse (client REPLY-blocked in all three looks, loop still running) from a lost reply, nor a loop that spins on the
 * CPU from a healthy one; the judge now asks «did the count grow». /tmp is a RAM link (check.sh), so this count does
 * not wait for the disk driver the way the v3 reproducibility observer did.
 *
 * MSGS1 (2026-11-22, before sealed v6): the message records are read with each of the two TICK counts (MSGS1, then
 * MSGS). A «fix» that exchanges a few messages and then only ticks passed while they were read once (dev check
 * fake_fix_check.py --tick-first). Both readings are taken before anything is printed. */
#include <dirent.h>
#include <fcntl.h>
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

static void pidin_to(const char *arg, const char *path) {   /* pidin [arg] > path, without touching the console */
  pid_t p = fork();
  if (p == 0) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd >= 0) { dup2(fd, 1); dup2(fd, 2); close(fd); }
    execl("/proc/boot/pidin", "pidin", arg, (char *)NULL); execlp("pidin", "pidin", arg, (char *)NULL); _exit(127);
  }
  if (p > 0) waitpid(p, NULL, 0);
}

static void cat(const char *path) {
  FILE *f = fopen(path, "r");
  char buf[4096];
  size_t n;
  while (f && (n = fread(buf, 1, sizeof buf, f)) > 0) fwrite(buf, 1, n, stdout);
  if (f) fclose(f);
  fflush(stdout);
}

static void count_ticks(char *out, size_t cap) {   /* one "/tmp/d0<role>.log <n>" line per role log */
  char path[300];
  size_t n = 0;
  DIR *d = opendir("/tmp");
  struct dirent *e;
  out[0] = 0;
  while (d && (e = readdir(d)) && n < cap - 400) {
    size_t l = strlen(e->d_name);
    if (strncmp(e->d_name, "d0", 2) || l < 6 || strcmp(e->d_name + l - 4, ".log")) continue;
    snprintf(path, sizeof path, "/tmp/%s", e->d_name);
    n += snprintf(out + n, cap - n, "%s %d\n", path, ticks(path));
  }
  if (d) closedir(d);
}

static void read_msgs(char *out, size_t cap) {   /* "<pid> <record>" for every qd_trace record */
  char path[300], line[128];
  size_t n = 0;
  DIR *d = opendir("/dev/shmem");
  struct dirent *e;
  out[0] = 0;
  while (d && (e = readdir(d))) {
    if (strncmp(e->d_name, "qdm.", 4)) continue;
    snprintf(path, sizeof path, "/dev/shmem/%s", e->d_name);
    FILE *f = fopen(path, "r");
    while (f && n + 256 < cap && fgets(line, sizeof line, f)) {
      size_t l = strlen(line);
      while (l && (line[l - 1] == '\n' || line[l - 1] == ' ')) line[--l] = 0;
      if (l) n += snprintf(out + n, cap - n, "%.24s %s\n", e->d_name + 4, line);
    }
    if (f) fclose(f);
  }
  if (d) closedir(d);
}

int main(void) {
  sigset_t s;
  sigemptyset(&s); sigaddset(&s, SIGUSR1);
  sigprocmask(SIG_BLOCK, &s, NULL);
  pthread_setschedprio(pthread_self(), 63);
  int sig = 0;
  sigwait(&s, &sig);
  static char out[4096], out2[4096], msgs1[65536], msgs[65536];
  count_ticks(out, sizeof out);
  read_msgs(msgs1, sizeof msgs1);
  pidin_to(NULL, "/dev/shmem/qd.pidin");
  pidin_to("arg", "/dev/shmem/qd.args");
  usleep(300000); pidin_to(NULL, "/dev/shmem/qd.pidin2");   /* two more looks a moment later: a chain must persist */
  usleep(300000); pidin_to(NULL, "/dev/shmem/qd.pidin3");
  usleep(1500000); count_ticks(out2, sizeof out2);   /* progress: the same logs counted again */
  read_msgs(msgs, sizeof msgs);
  puts("=== PIDIN ==="); cat("/dev/shmem/qd.pidin");
  printf("=== TICKS ===\n%s", out);
  puts("=== ARGS ==="); cat("/dev/shmem/qd.args");
  puts("=== PIDIN2 ==="); cat("/dev/shmem/qd.pidin2");
  puts("=== PIDIN3 ==="); cat("/dev/shmem/qd.pidin3");
  printf("=== TICKS2 ===\n%s", out2);
  printf("=== MSGS1 ===\n%s", msgs1);
  printf("=== MSGS ===\n%s", msgs);
  puts("=== END ==="); fflush(stdout);
  return 0;
}
