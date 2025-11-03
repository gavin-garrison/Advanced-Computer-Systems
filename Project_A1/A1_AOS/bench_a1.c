#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <errno.h>
#include <unistd.h>
#include <sched.h>
#include <sys/mman.h>

static double now_s(void){
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return ts.tv_sec + ts.tv_nsec*1e-9;
}

static int set_affinity(int cpu){
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
}

static void clobber() { asm volatile("":::"memory"); }

// Simple compute loop to burn CPU (FMA-like)
static double compute_bench(size_t iters){
    double t0 = now_s();
    volatile double a=1.1, b=1.3, c=1.7, d=0.0;
    for(size_t i=0;i<iters;i++){
        d += a*b + c;
        a += 0.0000001;
        b += 0.0000002;
        c -= 0.0000003;
        if ((i & 0x3FFFF) == 0) clobber();
    }
    double t1 = now_s();
    // Prevent optimization
    fprintf(stderr, "compute_sink=%f\n", (double)d);
    return (t1 - t0);
}

// Touch buffer to ensure allocation (and THP opportunity)
static void touch_pages(char* buf, size_t bytes){
    size_t page = 4096;
    for(size_t i=0;i<bytes; i+=page){
        buf[i]++;
    }
}

// Memcpy throughput test (optionally using hugepage advice)
static double memcpy_bench(size_t bytes, int iters, int use_thp){
    char* src = (char*)aligned_alloc(4096, bytes);
    char* dst = (char*)aligned_alloc(4096, bytes);
    if(!src || !dst){ perror("alloc"); exit(1); }
    memset(src, 1, bytes);
    memset(dst, 2, bytes);

    if(use_thp){
#ifdef MADV_HUGEPAGE
        madvise(src, bytes, MADV_HUGEPAGE);
        madvise(dst, bytes, MADV_HUGEPAGE);
#endif
    } else {
#ifdef MADV_NOHUGEPAGE
        madvise(src, bytes, MADV_NOHUGEPAGE);
        madvise(dst, bytes, MADV_NOHUGEPAGE);
#endif
    }
    touch_pages(src, bytes);
    touch_pages(dst, bytes);

    double t0 = now_s();
    for(int i=0;i<iters;i++){
        memcpy(dst, src, bytes);
        clobber();
    }
    double t1 = now_s();
    // prevent optimization
    fprintf(stderr, "memcpy_sink=%d\n", dst[0]);
    free(src); free(dst);
    return (t1 - t0);
}

// Strided read sum to probe prefetcher/cache
static double stride_bench(size_t bytes, size_t stride){
    size_t n = bytes / sizeof(uint64_t);
    uint64_t* arr = (uint64_t*)aligned_alloc(4096, n*sizeof(uint64_t));
    if(!arr){ perror("alloc"); exit(1); }
    for(size_t i=0;i<n;i++) arr[i]=i;
    touch_pages((char*)arr, n*sizeof(uint64_t));

    volatile uint64_t sum=0;
    double t0 = now_s();
    for(size_t i=0;i<n; i += stride/sizeof(uint64_t)){
        sum += arr[i];
        if ((i & 0x3FFFF) == 0) clobber();
    }
    double t1 = now_s();
    fprintf(stderr, "stride_sum=%llu\n", (unsigned long long)sum);
    free((void*)arr);
    return (t1 - t0);
}

typedef struct {
    int cpu;
    size_t iters;
    size_t bytes;
    int role; // 0 victim (memcpy), 1 interferer (compute)
    int use_thp;
} th_args;

void* smt_thread(void* arg){
    th_args* a = (th_args*)arg;
    if(a->cpu >= 0) set_affinity(a->cpu);
    double t=0.0;
    if(a->role==0){
        t = memcpy_bench(a->bytes, 10, a->use_thp);
        printf("VICTIM_time_s,%.6f\n", t);
    }else{
        t = compute_bench(a->iters);
        printf("INTERFERER_time_s,%.6f\n", t);
    }
    return NULL;
}

/*
USAGE:
  ./bench_a1 affinity --cpu=0 --iters=200000000
  ./bench_a1 thp --bytes=1073741824 --iters=5 --thp=1|0
  ./bench_a1 stride --bytes=134217728 --stride=64|128|256|...
  ./bench_a1 smt --victim-cpu=0 --interf-cpu=1 --bytes=268435456 --iters=200000000 --thp=1
*/
static int argi(const char* key, int def, int argc, char** argv){
    for(int i=0;i<argc;i++){
        if(strncmp(argv[i], key, strlen(key))==0){
            return atoi(argv[i]+strlen(key));
        }
    }
    return def;
}

static size_t argsz(const char* key, size_t def, int argc, char** argv){
    for(int i=0;i<argc;i++){
        if(strncmp(argv[i], key, strlen(key))==0){
            return (size_t) strtoull(argv[i]+strlen(key), NULL, 10);
        }
    }
    return def;
}

int main(int argc, char** argv){
    if(argc<2){
        fprintf(stderr, "modes: affinity | thp | stride | smt\n");
        return 1;
    }
    const char* mode = argv[1];

    if(strcmp(mode,"affinity")==0){
        int cpu = argi("--cpu=", -1, argc, argv);
        size_t iters = (size_t)argsz("--iters=", 200000000ULL, argc, argv);
        if(cpu>=0){
            if(set_affinity(cpu)!=0) perror("set_affinity");
        }
        double t = compute_bench(iters);
        printf("mode,affinity,cpu,%d,iters,%zu,time_s,%.6f\n", cpu, iters, t);
        return 0;
    }

    if(strcmp(mode,"thp")==0){
        size_t bytes = argsz("--bytes=", 1ULL<<30, argc, argv); // 1 GiB default
        int iters = argi("--iters=", 5, argc, argv);
        int thp = argi("--thp=", 1, argc, argv);
        double t = memcpy_bench(bytes, iters, thp);
        double gb = (bytes*(double)iters)/1e9;
        double gbps = gb / t;
        printf("mode,thp,bytes,%zu,iters,%d,thp_flag,%d,time_s,%.6f,GB_copied,%.3f,GBps,%.3f\n",
               bytes, iters, thp, t, gb, gbps);
        return 0;
    }

    if(strcmp(mode,"stride")==0){
        size_t bytes = argsz("--bytes=", 128ULL<<20, argc, argv); // 128 MiB
        size_t stride = argsz("--stride=", 64, argc, argv);
        double t = stride_bench(bytes, stride);
        size_t steps = (bytes/sizeof(uint64_t)) / (stride/sizeof(uint64_t));
        double ns_per_access = (t*1e9)/ (steps?steps:1);
        printf("mode,stride,bytes,%zu,strideB,%zu,time_s,%.6f,ns_per_access,%.2f\n",
               bytes, stride, t, ns_per_access);
        return 0;
    }

    if(strcmp(mode,"smt")==0){
        int vcpu = argi("--victim-cpu=", 0, argc, argv);
        int icpu = argi("--interf-cpu=", 1, argc, argv);
        size_t iters = (size_t)argsz("--iters=", 200000000ULL, argc, argv);
        size_t bytes = argsz("--bytes=", 256ULL<<20, argc, argv);
        int thp = argi("--thp=", 1, argc, argv);

        pthread_t tv, ti;
        th_args av = {.cpu=vcpu, .iters=iters, .bytes=bytes, .role=0, .use_thp=thp};
        th_args ai = {.cpu=icpu, .iters=iters, .bytes=bytes, .role=1, .use_thp=thp};

        double t0 = now_s();
        if(pthread_create(&tv, NULL, smt_thread, &av)!=0){perror("pthread_create"); exit(1);}
        if(pthread_create(&ti, NULL, smt_thread, &ai)!=0){perror("pthread_create"); exit(1);}
        pthread_join(tv, NULL);
        pthread_join(ti, NULL);
        double t1 = now_s();
        printf("mode,smt,victim_cpu,%d,interf_cpu,%d,bytes,%zu,iters,%zu,thp,%d,total_time_s,%.6f\n",
               vcpu, icpu, bytes, iters, thp, (t1-t0));
        return 0;
    }

    fprintf(stderr, "unknown mode\n");
    return 1;
}
