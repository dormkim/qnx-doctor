/* chain_s2 <me> <s3>: middle stage, runs at a background priority. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1],*s3=argv[2]; pthread_setschedprio(pthread_self(),12);
  name_attach_t*a=name_attach(NULL,me,_NTO_CHF_FIXED_PRIORITY); if(!a){perror("na");return 1;}
  int co=qd_open(s3); qd_msg_t m;
  for(int n=0;;n++){ int r=qd_receive(a->chid,&m); if(r>0){ qd_send(co,n); MsgReply(r,EOK,0,0);} qd_tick(me,n); }
}
