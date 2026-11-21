#include "session_manager.h"

#include <stdio.h>
#include <sys/stat.h>

namespace scooterlab {

bool next_session_path(const char *sessions_dir,
                       char *out_path,
                       size_t out_path_len,
                       char *out_name,
                       size_t out_name_len) {
    if (sessions_dir == nullptr || out_path == nullptr || out_name == nullptr) {
        return false;
    }
    for (unsigned int idx = 1; idx <= 99999; ++idx) {
        snprintf(out_name, out_name_len, "sess%05u.slab", idx);
        snprintf(out_path, out_path_len, "%s/%s", sessions_dir, out_name);
        struct stat st{};
        if (stat(out_path, &st) != 0) {
            return true;
        }
    }
    return false;
}

bool is_session_uploaded(const char *slab_path) {
    if (slab_path == nullptr) {
        return false;
    }
    char marker[300];
    snprintf(marker, sizeof(marker), "%s.uploaded", slab_path);
    struct stat st{};
    return stat(marker, &st) == 0;
}

bool mark_session_uploaded(const char *slab_path) {
    if (slab_path == nullptr) {
        return false;
    }
    char marker[300];
    snprintf(marker, sizeof(marker), "%s.uploaded", slab_path);
    FILE *fp = fopen(marker, "wb");
    if (fp == nullptr) {
        return false;
    }
    fputs("ok\n", fp);
    fclose(fp);
    return true;
}

} // namespace scooterlab
