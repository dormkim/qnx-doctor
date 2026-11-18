/* pp_client <me> <peer>: request with a 1s send guard. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; pthread_setschedprio(pthread_self(),30);
  int coid=qd_open_fixed(peer);
  for(int n=0;;n++){
    uint64_t to=1ULL*1000*1000*1000*3600;   /* QD-CULPRIT: '1s' guard is really 3600s */
    TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_REPLY,NULL,&to,NULL);
    qd_send(coid,n); qd_tick(me,n); usleep(120000);
  }
}
