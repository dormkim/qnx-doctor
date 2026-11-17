/* abba <a> <b>: two workers guard two resources. */
#include "../common/qd.h"
static pthread_mutex_t m1,m2; static const char*R[2];
static FILE* lg(const char*r){char p[64];snprintf(p,sizeof p,"/tmp/%s.log",r);return fopen(p,"w");}
static void tk(FILE*f,const char*r,int n){fprintf(f,"TICK %s %d\n",r,n);fflush(f);}
static void*wa(void*_){FILE*f=lg(R[0]);tk(f,R[0],0);
  pthread_mutex_lock(&m1);tk(f,R[0],1);usleep(150000);
  pthread_mutex_lock(&m2);                 /* wants m2 while holding m1 */
  tk(f,R[0],2);pthread_mutex_unlock(&m2);pthread_mutex_unlock(&m1);
  for(int n=3;;n++){tk(f,R[0],n);usleep(120000);} return 0;}
static void*wb(void*_){FILE*f=lg(R[1]);tk(f,R[1],0);
  pthread_mutex_lock(&m2);tk(f,R[1],1);usleep(150000);
  pthread_mutex_lock(&m1);                 /* wants m1 while holding m2 */
  tk(f,R[1],2);pthread_mutex_unlock(&m1);pthread_mutex_unlock(&m2);
  for(int n=3;;n++){tk(f,R[1],n);usleep(120000);} return 0;}
int main(int argc,char**argv){
  R[0]=argv[1];R[1]=argv[2]; pthread_mutex_init(&m1,0);pthread_mutex_init(&m2,0);
  pthread_t a,b; pthread_create(&a,0,wa,0);pthread_create(&b,0,wb,0);
  pthread_join(a,0);pthread_join(b,0); return 0;
}
