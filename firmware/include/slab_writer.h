#pragma once
/**
 * ScooterLab deterministic `.slab` v1 binary writer with incremental IEEE 802.3 CRC32.
 * Compiles both on ESP-IDF (microSD FATFS) and host C++17 (unit/cross-language tests).
 */

#include <stdint.h>
#include <stdio.h>
#include "slab_format.h"

namespace scooterlab {

uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len);
uint32_t crc32_ieee(const uint8_t *data, size_t len);

class SlabWriter {
public:
    SlabWriter() = default;
    ~SlabWriter();

    SlabWriter(const SlabWriter &) = delete;
    SlabWriter &operator=(const SlabWriter &) = delete;

    bool open(const char *path,
              uint8_t build_level,
              uint16_t imu_hz,
              uint16_t gps_hz,
              uint16_t flags,
              uint32_t start_epoch_s);

    bool write_imu(const slab_imu_rec_t &rec);
    bool write_gps(const slab_gps_rec_t &rec);

    // Flushes buffered data, writes footer `"END!"` + payload CRC32, patches
    // header record_count + header CRC32, calls fsync(), and closes the file.
    bool close_safe();

    bool is_open() const { return fp_ != nullptr; }
    uint32_t record_count() const { return record_count_; }

private:
    bool write_record(uint8_t rec_type, const void *payload, uint8_t len);

    FILE *fp_ = nullptr;
    slab_header_t header_{};
    uint32_t record_count_ = 0;
    uint32_t payload_crc_ = 0xFFFFFFFFu;
};

} // namespace scooterlab
