/* timed_client <me> <peer>: guarded request (1s receive timeout). */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; int coid=qd_open(peer);
  for(int n=0;;n++){
    uint64_t to=1000000000ULL;
    TimerTimeout(CLOCK_MONOTONIC,_NTO_TIMEOUT_RECEIVE,NULL,&to,NULL);  /* guards RECEIVE, but we SEND */
    qd_send(coid,n); qd_tick(me,n); usleep(120000);
  }
}
