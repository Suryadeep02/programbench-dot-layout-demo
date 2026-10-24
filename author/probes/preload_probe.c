#include <stdio.h>

__attribute__((constructor)) static void mark_preload(void) {
    FILE *f = fopen("/tmp/preload_succeeded", "w");
    if (f) {
        fputs("injected\n", f);
        fclose(f);
    }
}
