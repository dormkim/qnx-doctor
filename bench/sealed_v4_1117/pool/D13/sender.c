/* sender <me> <peer> <period_ms>: fire a request every <period_ms>. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; int ms=atoi(argv[3]); int coid=qd_open(peer);
  for(int n=0;;n++){ qd_send(coid,n); qd_tick(me,n); usleep(ms*1000); }
}
