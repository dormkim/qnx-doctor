/* chain_s1 <me> <s2>: front of a 3-stage pipeline. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*s2=argv[2]; name_attach_t*a=qd_attach(me); int co=qd_open(s2); qd_msg_t m;
  for(int n=0;;n++){ int r=qd_receive(a->chid,&m); if(r>0){ qd_send(co,n); MsgReply(r,EOK,0,0);} qd_tick(me,n); }
}
