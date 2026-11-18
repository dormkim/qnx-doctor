/* lowsrv <me> <prio>: background server on a fixed-priority channel (no inheritance). */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; int prio=atoi(argv[2]); setprio(pid,prio);
  int chid=qd_fixed_chan(me);  /* QD-CULPRIT: _NTO_CHF_FIXED_PRIORITY -> server keeps its low prio, never inherits the client */
  qd_msg_t m;
  for(int n=0;;n++){ int r=qd_receive(chid,&m); if(r>0) MsgReply(r,EOK,0,0); qd_tick(me,n); }
}
