/* lowfix_srv <me>: a background server, pinned low, channel fixed-priority. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; pthread_setschedprio(pthread_self(),12);
  name_attach_t*a=name_attach(NULL,me,_NTO_CHF_FIXED_PRIORITY);  /* stays at 12, won't inherit the caller */
  if(!a){perror("name_attach");return 1;}
  qd_msg_t m;
  for(int n=0;;n++){ int r=qd_receive(a->chid,&m); if(r>0) MsgReply(r,EOK,0,0); qd_tick(me,n); }
}
