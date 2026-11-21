#pragma once
/**
 * ScooterLab Smart IMU Driver — ST ISM330IS on SPI2 (ADR-0002 / ADR-0006).
 * Pure burst parsing & scaling compiles on host C++17; SPI bus I/O runs under ESP_PLATFORM.
 */

#include <stdint.h>
#include "slab_format.h"

namespace scooterlab {

static constexpr uint8_t ISM330IS_REG_WHO_AM_I = 0x0F;
static constexpr uint8_t ISM330IS_WHO_AM_I_VAL = 0x22;
static constexpr uint8_t ISM330IS_REG_CTRL1_XL = 0x10;
static constexpr uint8_t ISM330IS_REG_CTRL2_G = 0x11;
static constexpr uint8_t ISM330IS_REG_OUTX_L_G = 0x22; // 12 bytes: G(6) + XL(6)

// Sensitivity for +/-8g (0.244 mg/LSB) and +/-1000 dps (35 mdps/LSB = 0.35 ddps/LSB)
int16_t ism330is_raw_to_mg_8g(int16_t raw);
int16_t ism330is_raw_to_ddps_1000dps(int16_t raw);

// Parse 12-byte SPI burst starting at OUTX_L_G (GX, GY, GZ, AX, AY, AZ little-endian)
void ism330is_parse_burst_12b(const uint8_t raw[12], uint32_t t_ms, slab_imu_rec_t &out);

#ifdef ESP_PLATFORM
bool ism330is_init_spi2();
bool ism330is_read_sample(uint32_t t_ms, slab_imu_rec_t &out);
#endif

} // namespace scooterlab
