#pragma once
/**
 * ScooterLab ignition & battery voltage monitor (ADR-0002 / TASK-HW-03).
 *
 * Voltage divider on IGN_SENSE (GPIO4): R1=47k, R2=10k -> scale = 5.7x
 * Maps 14.8V charging voltage to ~2.60V (safe for ESP32-S3 3.3V ADC).
 * When IGN drops below `kIgnOffThresholdMv` (6.0V), triggers immediate
 * `SlabWriter::close_safe()` while hold-up capacitor sustains 5V rail >=200ms.
 */

#include <stdint.h>

namespace scooterlab {

enum class PowerState : uint8_t {
    IGN_OFF = 0,
    BATTERY_LOW = 1,       // < 12.1 V (engine off / weak battery)
    NOMINAL_IDLE = 2,      // 12.1 - 13.3 V (key ON, engine off)
    CHARGING_OK = 3,       // 13.4 - 14.9 V (SYM regulator healthy [XB20])
    OVER_VOLTAGE = 4,      // >= 15.0 V (regulator fault warning!)
};

static constexpr uint32_t kDividerNum = 57;   // (47k + 10k) / 10k = 5.7
static constexpr uint32_t kDividerDen = 10;
static constexpr uint32_t kIgnOffThresholdMv = 6000;

uint32_t adc_mv_to_vbat_mv(uint32_t adc_mv);
PowerState classify_vbat_mv(uint32_t vbat_mv);
bool should_trigger_safe_shutdown(uint32_t vbat_mv);

} // namespace scooterlab
