/* relay_cli <me> <peer>: knock every 150ms. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*peer=argv[2]; int coid=qd_open(peer);
  for(int n=0;;n++){ qd_send(coid,n); qd_tick(me,n); usleep(150000); }
}
