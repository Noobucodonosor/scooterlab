#pragma once
/**
 * ScooterLab GNSS NMEA Parser — u-blox M10 on UART1 (ADR-0002 / ADR-0006).
 * Parses `$GNRMC`/`$GPRMC` and `$GNGGA`/`$GPGGA` sentences with checksum validation.
 */

#include <stdint.h>
#include "slab_format.h"

namespace scooterlab {

bool nmea_verify_checksum(const char *sentence);
bool nmea_parse_line(const char *sentence, uint32_t t_ms, slab_gps_rec_t &state);

#ifdef ESP_PLATFORM
bool gnss_init_uart1();
#endif

} // namespace scooterlab
