#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <process.h>

int main(int argc, char *argv[]) {
    char *new_argv[argc + 2];
    int new_argc = 0;
    
    new_argv[new_argc++] = "rg_real.exe";
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-r") == 0) {
            continue;
        }
        // Quote arguments with spaces
        if (strchr(argv[i], ' ') != NULL && argv[i][0] != '"') {
            char *quoted = malloc(strlen(argv[i]) + 3);
            sprintf(quoted, "\"%s\"", argv[i]);
            new_argv[new_argc++] = quoted;
        } else {
            new_argv[new_argc++] = argv[i];
        }
    }
    
    new_argv[new_argc++] = ".";
    new_argv[new_argc] = NULL;
    
    execvp("rg_real.exe", new_argv);
    return 1;
}
