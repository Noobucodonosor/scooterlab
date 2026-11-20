#pragma once
/**
 * ScooterLab HTTPS TLS 1.3 + Bearer Token session uploader (ADR-0003 / TASK-SEC-03).
 * Streams `.slab` files from microSD in 4 KB chunks to avoid RAM exhaustion.
 */

#include <stdbool.h>
#include "config_nvs.h"

namespace scooterlab {

struct UploadResult {
    bool ok;
    int http_status;
    size_t bytes_sent;
};

UploadResult upload_slab_https(const NvsConfig &cfg,
                               const char *local_slab_path,
                               const char *session_filename,
                               const char *ca_cert_pem);

} // namespace scooterlab
