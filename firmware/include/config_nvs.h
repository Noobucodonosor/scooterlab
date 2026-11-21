#pragma once
/**
 * ScooterLab encrypted NVS configuration loader (ADR-0003 / TASK-SEC-02).
 * Never falls back to hardcoded default passwords (RED EN 18031 compliant).
 */

#include <stdbool.h>
#include <stddef.h>

namespace scooterlab {

struct NvsConfig {
    char wifi_ssid[33];
    char wifi_pass[65];
    char ingest_url[128];
    char bearer_token[65];
};

// Loads provisioned credentials from encrypted ESP-IDF NVS namespace "scooterlab".
// Returns false if unprovisioned (device stays in offline microSD-only logging mode).
bool load_nvs_config(NvsConfig &out_cfg);

// Saves provisioned credentials into encrypted NVS (used during BLE/SoftAP first setup).
bool save_nvs_config(const NvsConfig &cfg);

// Validates that required fields are non-empty and ingest_url uses https://.
bool validate_nvs_config(const NvsConfig &cfg);

} // namespace scooterlab
