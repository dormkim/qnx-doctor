/* need_conf <me>: the upstream to pull from is named in our site config. */
#include "../common/qd.h"
int main(int argc,char**argv){
  const char*me=argv[1]; char peer[64]="";
  FILE*f=fopen("/var/qd/D18/upstream.conf","r");   /* not in this capture */
  if(f){ if(fgets(peer,sizeof peer,f)){} fclose(f); }
  name_attach_t*a=qd_attach(me); qd_tick(me,0); qd_msg_t m;
  for(int n=1;;n++){
    int r=qd_receive(a->chid,&m);   /* waits for the upstream named in the (absent) config */
    if(r>0) MsgReply(r,EOK,0,0); qd_tick(me,n);
  }
}
