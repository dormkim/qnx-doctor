/* reentr_s1 <me> <s2>: on each request, consult s2, then reply. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*s2=argv[2]; name_attach_t*a=qd_attach(me); int co=qd_open(s2); qd_msg_t m;
  for(int n=0;;n++){
    int r=qd_receive(a->chid,&m);
    if(r>0){ qd_send(co,n);        /* calls s2 while the caller waits (s2 calls back into us) */
             MsgReply(r,EOK,0,0); }
    qd_tick(me,n);
  }
}
