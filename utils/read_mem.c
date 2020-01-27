#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>


int main(int argc, char* argv[]){
    if(argc < 3){
        printf("%s", "Not enough arguments");
    }
    int pid = atoi(argv[1]);
    if (!pid && errno){
        return 1;
    }
    long long address = atoll(argv[2]);
    if (!address && errno){
        return 1;
    }
    char* mem_path = (char*)malloc(28); // The constant size of "/proc//mem\x00" + MAX_LONG_LONG length and then some
    sprintf(mem_path, "/proc/%d/mem", pid);
    int fd = open(mem_path, O_RDONLY);
    free(mem_path);
    ptrace(PTRACE_ATTACH, pid, NULL, NULL);
    int regs[45];
    ptrace(PTRACE_GETREGS, pid, NULL, &regs);
    waitpid(pid, NULL, 0);
    lseek(fd, address, SEEK_SET);
    char read_memory[4096] = {0};
    //write(fd, "\x42\x42\x42\x42\x42\x42\x42\x42\x42\x42\x42\x42", 0x10);
    //lseek(fd, -0x10, 1);
    ptrace(PTRACE_POKEDATA, pid, address, (int)0x39040000);
    read(fd, read_memory, 0x1000);
    printf("0x%x", atoi(read_memory));
    ptrace(PTRACE_DETACH, pid, NULL, NULL);
    close(fd);
    return 0;
}