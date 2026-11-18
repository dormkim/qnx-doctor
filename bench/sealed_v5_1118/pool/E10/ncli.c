/* ncli <me> <peer> <prio> <ms>: normal client; request every <ms> ms and get a reply. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; int prio=atoi(argv[3]); int ms=atoi(argv[4]);
  setprio(pid,prio); int coid=qd_open(peer);
  for(int n=0;;n++){ qd_send(coid,n); qd_tick(me,n); usleep(ms*1000); }
}
