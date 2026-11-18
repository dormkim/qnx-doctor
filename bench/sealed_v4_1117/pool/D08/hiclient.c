/* hiclient <me> <peer>: high-priority client, one request per 120ms. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; pthread_setschedprio(pthread_self(),30);
  int coid=qd_open_fixed(peer);
  for(int n=0;;n++){ qd_send(coid,n); qd_tick(me,n); usleep(120000); }
}
