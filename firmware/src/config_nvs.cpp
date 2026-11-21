#include "config_nvs.h"

#include <string.h>

#ifdef ESP_PLATFORM
#include "nvs.h"
#include "nvs_flash.h"
#endif

namespace scooterlab {

#ifdef ESP_PLATFORM
static constexpr const char *kNvsNamespace = "scooterlab";
#endif

bool validate_nvs_config(const NvsConfig &cfg) {
    if (cfg.wifi_ssid[0] == '\0' || cfg.wifi_pass[0] == '\0') {
        return false;
    }
    if (cfg.bearer_token[0] == '\0' || strlen(cfg.bearer_token) < 16) {
        return false;
    }
    // Enforce TLS (ADR-0003): reject cleartext http:// endpoints
    if (strncmp(cfg.ingest_url, "https://", 8) != 0) {
        return false;
    }
    return true;
}

bool load_nvs_config(NvsConfig &out_cfg) {
    memset(&out_cfg, 0, sizeof(out_cfg));
#ifdef ESP_PLATFORM
    nvs_handle_t handle = 0;
    if (nvs_open(kNvsNamespace, NVS_READONLY, &handle) != ESP_OK) {
        return false;
    }

    size_t len_ssid = sizeof(out_cfg.wifi_ssid);
    size_t len_pass = sizeof(out_cfg.wifi_pass);
    size_t len_url = sizeof(out_cfg.ingest_url);
    size_t len_tok = sizeof(out_cfg.bearer_token);

    bool ok =
        nvs_get_str(handle, "wifi_ssid", out_cfg.wifi_ssid, &len_ssid) == ESP_OK &&
        nvs_get_str(handle, "wifi_pass", out_cfg.wifi_pass, &len_pass) == ESP_OK &&
        nvs_get_str(handle, "ingest_url", out_cfg.ingest_url, &len_url) == ESP_OK &&
        nvs_get_str(handle, "bearer_tok", out_cfg.bearer_token, &len_tok) == ESP_OK;

    nvs_close(handle);
    return ok && validate_nvs_config(out_cfg);
#else
    return false;
#endif
}

bool save_nvs_config(const NvsConfig &cfg) {
    if (!validate_nvs_config(cfg)) {
        return false;
    }
#ifdef ESP_PLATFORM
    nvs_handle_t handle = 0;
    if (nvs_open(kNvsNamespace, NVS_READWRITE, &handle) != ESP_OK) {
        return false;
    }
    bool ok =
        nvs_set_str(handle, "wifi_ssid", cfg.wifi_ssid) == ESP_OK &&
        nvs_set_str(handle, "wifi_pass", cfg.wifi_pass) == ESP_OK &&
        nvs_set_str(handle, "ingest_url", cfg.ingest_url) == ESP_OK &&
        nvs_set_str(handle, "bearer_tok", cfg.bearer_token) == ESP_OK &&
        nvs_commit(handle) == ESP_OK;
    nvs_close(handle);
    return ok;
#else
    return true;
#endif
}

} // namespace scooterlab
