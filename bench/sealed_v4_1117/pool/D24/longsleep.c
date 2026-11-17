/* longsleep <me>: back off, then resume. */
#include "../common/qd.h"
#include <time.h>
int main(int argc,char**argv){
  const char*me=argv[1]; qd_tick(me,0);
  long base=3600;                 /* intended ~1s backoff */
  struct timespec ts; ts.tv_sec=base*1000; ts.tv_nsec=0;   /* QD-CULPRIT: *1000 -> 3,600,000 s */
  nanosleep(&ts,NULL);
  for(int n=1;;n++){ qd_tick(me,n); usleep(200000); }
}
