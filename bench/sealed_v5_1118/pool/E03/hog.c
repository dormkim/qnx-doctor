/* hog <me> <prio>: a mid-priority compute load. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; int prio=atoi(argv[2]); setprio(pid,prio);
  qd_tick(me,0); volatile long x=0; for(;;) x++;
}
