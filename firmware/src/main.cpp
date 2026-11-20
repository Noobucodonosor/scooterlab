/**
 * ScooterLab Edge Telemetry Logger — ESP-IDF v6.x (ADR-0002 / ADR-0003)
 *
 * Modules integrated:
 * - `config_nvs`: encrypted NVS credentials (zero hardcoded passwords, EN 18031)
 * - `slab_writer`: deterministic `.slab` v1 logging with incremental CRC32 + fsync
 * - `power_monitor`: IGN_SENSE ADC divider (47k/10k) for SYM regulator health & safe shutdown
 * - `uploader`: chunked HTTPS TLS 1.3 + Bearer Token upload on garage Wi-Fi
 */

#include <stdio.h>
#include "config_nvs.h"
#include "power_monitor.h"
#include "slab_format.h"
#include "slab_writer.h"
#include "uploader.h"

#ifndef BUILD_LEVEL
#define BUILD_LEVEL 0
#endif

#ifndef IMU_SAMPLE_HZ
#define IMU_SAMPLE_HZ 100
#endif

#ifndef GPS_SAMPLE_HZ
#define GPS_SAMPLE_HZ 5
#endif

extern "C" void app_main(void) {
    printf("[ScooterLab] Booting firmware (BUILD_LEVEL=%d, SLAB v%u, IMU=%dHz, GPS=%dHz)\n",
           BUILD_LEVEL, SLAB_VERSION, IMU_SAMPLE_HZ, GPS_SAMPLE_HZ);

    scooterlab::NvsConfig cfg{};
    const bool provisioned = scooterlab::load_nvs_config(cfg);
    if (!provisioned) {
        printf("[ScooterLab] NVS non provisionata: modalita solo logging offline microSD\n");
    } else {
        printf("[ScooterLab] NVS cifrata caricata: upload HTTPS pronto per %s\n", cfg.ingest_url);
    }

    // Hardware runtime loop (da completare al banco con MCU + IMU SPI + GNSS UART):
    // 1. Mount High Endurance microSD FAT32 e apertura sessione via `SlabWriter::open(...)`
    // 2. Sampling loop Smart IMU (ISM330IS/BHI360 SPI) + GNSS (UART1) -> `write_imu` / `write_gps`
    // 3. Controllo periodico `IGN_SENSE` -> se `should_trigger_safe_shutdown(vbat_mv)` chiama `close_safe()`
    // 4. Al rientro in garage (Wi-Fi connesso e `provisioned`) -> `upload_slab_https(...)`
}
