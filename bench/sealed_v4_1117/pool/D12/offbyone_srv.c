/* offbyone_srv <me>: reply to the previous caller once the next arrives. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; name_attach_t*a=qd_attach(me); qd_msg_t m; int prev=-1;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);
    if(prev>0) MsgReply(prev,EOK,0,0);   /* QD-CULPRIT: replies the PREVIOUS rcvid, not this one */
    if(r>0) prev=r;
    qd_tick(me,n);
  }
}
