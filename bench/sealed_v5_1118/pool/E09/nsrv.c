/* nsrv <me> <prio>: a normal name_attach server (inherits the client's priority); replies to every request. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; int prio=atoi(argv[2]); setprio(pid,prio);
  name_attach_t*a=qd_attach(me); qd_msg_t m;
  for(int n=0;;n++){ int r=qd_receive(a->chid,&m); if(r>0) MsgReply(r,EOK,&n,sizeof n); qd_tick(me,n); }
}
