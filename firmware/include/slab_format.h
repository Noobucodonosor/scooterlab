#pragma once
/**
 * ScooterLab binary telemetry format (.slab v1)
 * Aligned byte-for-byte with `tools/slab_codec.py` and `docs/04-formato-slab.md`.
 */

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

static constexpr uint8_t SLAB_VERSION = 1;
static constexpr uint8_t SLAB_REC_IMU = 1;
static constexpr uint8_t SLAB_REC_GPS = 2;
static constexpr uint8_t SLAB_REC_CAN = 3;
static constexpr uint8_t SLAB_REC_HEALTH = 4;

typedef struct __attribute__((packed)) {
    char magic[4];          // "SLAB"
    uint8_t version;        // 1
    uint8_t build_level;    // 0, 1, 2
    uint16_t imu_hz;        // e.g. 100
    uint16_t gps_hz;        // e.g. 5
    uint16_t flags;         // bit 0: ISPU, bit 1: CAN
    uint32_t start_epoch_s; // UTC epoch seconds
    uint32_t record_count;  // total records
    uint8_t reserved[8];    // zero-filled
    uint32_t header_crc32;  // CRC32 of first 28 bytes
} slab_header_t;

typedef struct __attribute__((packed)) {
    uint8_t rec_type;       // 1=IMU, 2=GPS, 3=CAN
    uint8_t rec_len;        // payload bytes
    uint16_t reserved;      // 0
} slab_rec_hdr_t;

typedef struct __attribute__((packed)) {
    uint32_t t_ms;
    int16_t ax_mg;
    int16_t ay_mg;
    int16_t az_mg;
    int16_t gx_ddps;
    int16_t gy_ddps;
    int16_t gz_ddps;
    int16_t roll_cdeg;
    int16_t pitch_cdeg;
} slab_imu_rec_t;

typedef struct __attribute__((packed)) {
    uint32_t t_ms;
    int32_t lat_e7;
    int32_t lon_e7;
    uint16_t speed_cms;
    uint16_t alt_dm;        // decimeters + 1000m offset
    uint8_t sats;
    uint8_t fix;            // 0=none, 2=2D, 3=3D
    uint16_t hdop_x10;
} slab_gps_rec_t;

typedef struct __attribute__((packed)) {
    uint32_t t_ms;
    uint32_t can_id;
    uint8_t dlc;
    uint8_t reserved[3];
    uint8_t data[8];
} slab_can_rec_t;

typedef struct __attribute__((packed)) {
    uint32_t t_ms;
    uint16_t vbat_mv;       // SYM regulator voltage (mV)
    int16_t temp_dc;        // Enclosure temp (deci-Celsius, e.g. 255 = 25.5 C)
} slab_health_rec_t;

typedef struct __attribute__((packed)) {
    char magic[4];          // "END!"
    uint32_t payload_crc32; // CRC32 of all record bytes
} slab_footer_t;

#ifdef __cplusplus
static_assert(sizeof(slab_header_t) == 32, "slab_header_t must be 32 bytes");
static_assert(sizeof(slab_rec_hdr_t) == 4, "slab_rec_hdr_t must be 4 bytes");
static_assert(sizeof(slab_imu_rec_t) == 20, "slab_imu_rec_t must be 20 bytes");
static_assert(sizeof(slab_gps_rec_t) == 20, "slab_gps_rec_t must be 20 bytes");
static_assert(sizeof(slab_can_rec_t) == 20, "slab_can_rec_t must be 20 bytes");
static_assert(sizeof(slab_health_rec_t) == 8, "slab_health_rec_t must be 8 bytes");
static_assert(sizeof(slab_footer_t) == 8, "slab_footer_t must be 8 bytes");
}
#endif
