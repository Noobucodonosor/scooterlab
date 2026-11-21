#include "uploader.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#ifdef ESP_PLATFORM
#include "esp_http_client.h"
#endif

namespace scooterlab {

UploadResult upload_slab_https(const NvsConfig &cfg,
                               const char *local_slab_path,
                               const char *session_filename,
                               const char *ca_cert_pem) {
    UploadResult res{false, 0, 0};
    if (!validate_nvs_config(cfg) || local_slab_path == nullptr || session_filename == nullptr) {
        return res;
    }

    struct stat st{};
    if (stat(local_slab_path, &st) != 0 || st.st_size <= 0) {
        return res;
    }

#ifdef ESP_PLATFORM
    if (ca_cert_pem == nullptr || ca_cert_pem[0] == '\0') {
        return res;
    }

    FILE *fp = fopen(local_slab_path, "rb");
    if (fp == nullptr) {
        return res;
    }

    esp_http_client_config_t http_cfg{};
    http_cfg.url = cfg.ingest_url;
    http_cfg.method = HTTP_METHOD_POST;
    http_cfg.cert_pem = ca_cert_pem;
    http_cfg.timeout_ms = 15000;

    esp_http_client_handle_t client = esp_http_client_init(&http_cfg);
    if (client == nullptr) {
        fclose(fp);
        return res;
    }

    char auth_hdr[96];
    snprintf(auth_hdr, sizeof(auth_hdr), "Bearer %s", cfg.bearer_token);
    esp_http_client_set_header(client, "Authorization", auth_hdr);
    memset(auth_hdr, 0, sizeof(auth_hdr));
    esp_http_client_set_header(client, "X-Session-Name", session_filename);
    esp_http_client_set_header(client, "Content-Type", "application/octet-stream");

    if (esp_http_client_open(client, st.st_size) == ESP_OK) {
        uint8_t buf[4096];
        size_t n = 0;
        bool write_ok = true;
        while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
            if (esp_http_client_write(client, reinterpret_cast<const char *>(buf), n) < 0) {
                write_ok = false;
                break;
            }
            res.bytes_sent += n;
        }
        if (write_ok && esp_http_client_fetch_headers(client) >= 0) {
            res.http_status = esp_http_client_get_status_code(client);
            res.ok = (res.http_status == 200);
        }
        esp_http_client_close(client);
    }

    esp_http_client_cleanup(client);
    fclose(fp);
#else
    (void)ca_cert_pem;
    res.bytes_sent = static_cast<size_t>(st.st_size);
    res.http_status = 200;
    res.ok = true;
#endif
    return res;
}

} // namespace scooterlab
