#include "power_monitor.h"

namespace scooterlab {

uint32_t adc_mv_to_vbat_mv(uint32_t adc_mv) {
    return (adc_mv * kDividerNum) / kDividerDen;
}

PowerState classify_vbat_mv(uint32_t vbat_mv) {
    if (vbat_mv < kIgnOffThresholdMv) {
        return PowerState::IGN_OFF;
    }
    if (vbat_mv < 12100) {
        return PowerState::BATTERY_LOW;
    }
    if (vbat_mv < 13400) {
        return PowerState::NOMINAL_IDLE;
    }
    if (vbat_mv < 15000) {
        return PowerState::CHARGING_OK;
    }
    return PowerState::OVER_VOLTAGE;
}

bool should_trigger_safe_shutdown(uint32_t vbat_mv) {
    return vbat_mv < kIgnOffThresholdMv;
}

} // namespace scooterlab
