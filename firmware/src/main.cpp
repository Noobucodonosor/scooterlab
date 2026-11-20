/**
 * ScooterLab Edge Telemetry Logger — ESP-IDF v6.x Scaffold (ADR-0002 / ADR-0003)
 *
 * Security-by-design (RED EN 18031 / CRA-ready):
 * - ZERO hardcoded Wi-Fi SSID/PASS or upload tokens in source code.
 * - Credentials loaded exclusively from encrypted NVS namespace "scooterlab".
 * - Deterministic `.slab` v1 logging to High Endurance microSD over SPI.
 * - Clean `fsync()` triggered by IGN_SENSE power-loss detection (hold-up cap).
 */

#include <stdio.h>
#include <string.h>
#include "slab_format.h"

#ifndef BUILD_LEVEL
#define BUILD_LEVEL 0
#endif

typedef struct {
    char wifi_ssid[33];
    char wifi_pass[65];
    char ingest_url[128];
    char bearer_token[65];
} scooterlab_nvs_config_t;

static bool load_config_from_encrypted_nvs(scooterlab_nvs_config_t *cfg) {
    // TODO(TASK-SEC-02): Read from encrypted ESP-IDF NVS partition ("scooterlab").
    // Never fall back to shared default passwords (EN 18031 requirement).
    memset(cfg, 0, sizeof(*cfg));
    return false;
}

extern "C" void app_main(void) {
    printf("[ScooterLab] Booting firmware (BUILD_LEVEL=%d, SLAB v%u)\n",
           BUILD_LEVEL, SLAB_VERSION);

    scooterlab_nvs_config_t cfg;
    if (!load_config_from_encrypted_nvs(&cfg)) {
        printf("[ScooterLab] NVS non provisionata: modalita solo logging offline microSD\n");
    }

    // Pipeline loop (TASK-HW-02 / TASK-HW-03):
    // 1. Init SPI2 bus -> Smart IMU (ISM330IS / BHI360) + High Endurance microSD
    // 2. Init UART1 -> GNSS 5-10 Hz
    // 3. Register IGN_SENSE interrupt for safe `.slab` footer + fsync() on key-off
    // 4. On garage Wi-Fi detection -> TLS 1.3 POST /upload with Bearer Token
}
