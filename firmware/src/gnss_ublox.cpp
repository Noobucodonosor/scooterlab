#include "gnss_ublox.h"
#include "board_pins.h"

#include <stdlib.h>
#include <string.h>

#ifdef ESP_PLATFORM
#include "driver/uart.h"
#endif

namespace scooterlab {

bool nmea_verify_checksum(const char *sentence) {
    if (sentence == nullptr || sentence[0] != '$') {
        return false;
    }
    uint8_t calc = 0;
    size_t i = 1;
    while (sentence[i] != '\0' && sentence[i] != '*') {
        calc ^= static_cast<uint8_t>(sentence[i]);
        ++i;
    }
    if (sentence[i] != '*' || sentence[i + 1] == '\0' || sentence[i + 2] == '\0') {
        return false;
    }
    char hex[3] = {sentence[i + 1], sentence[i + 2], '\0'};
    char *end = nullptr;
    unsigned long expected = strtoul(hex, &end, 16);
    return end == hex + 2 && calc == static_cast<uint8_t>(expected);
}

static int32_t parse_deg_min_e7(const char *field, char hemi, bool is_lon) {
    if (field == nullptr || field[0] == '\0') {
        return 0;
    }
    double raw = strtod(field, nullptr);
    int deg = static_cast<int>(raw / 100.0);
    double mins = raw - (deg * 100.0);
    double decimal = static_cast<double>(deg) + (mins / 60.0);
    if ((is_lon && hemi == 'W') || (!is_lon && hemi == 'S')) {
        decimal = -decimal;
    }
    return static_cast<int32_t>(decimal * 1e7);
}

bool nmea_parse_line(const char *sentence, uint32_t t_ms, slab_gps_rec_t &state) {
    if (!nmea_verify_checksum(sentence)) {
        return false;
    }

    char buf[128];
    strncpy(buf, sentence, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    char *star = strchr(buf, '*');
    if (star != nullptr) {
        *star = '\0';
    }

    const char *fields[20]{};
    int nf = 0;
    char *p = buf;
    while (nf < 20) {
        fields[nf++] = p;
        char *comma = strchr(p, ',');
        if (comma == nullptr) {
            break;
        }
        *comma = '\0';
        p = comma + 1;
    }

    if (nf < 6 || fields[0] == nullptr || strlen(fields[0]) < 3) {
        return false;
    }

    if (strcmp(fields[0] + 3, "RMC") == 0 && nf >= 8) {
        if (fields[2][0] != 'A') {
            state.fix = 0;
            return false;
        }
        state.t_ms = t_ms;
        state.lat_e7 = parse_deg_min_e7(fields[3], fields[4][0], false);
        state.lon_e7 = parse_deg_min_e7(fields[5], fields[6][0], true);
        double knots = strtod(fields[7], nullptr);
        state.speed_cms = static_cast<uint16_t>(knots * 51.4444); // 1 kn = 0.514444 m/s
        if (state.fix < 2) {
            state.fix = 2;
        }
        return true;
    }

    if (strcmp(fields[0] + 3, "GGA") == 0 && nf >= 10) {
        int q = atoi(fields[6]);
        state.t_ms = t_ms;
        state.fix = (q > 0) ? 3 : 0;
        state.sats = static_cast<uint8_t>(atoi(fields[7]));
        state.hdop_x10 = static_cast<uint16_t>(strtod(fields[8], nullptr) * 10.0);
        double alt_m = strtod(fields[9], nullptr);
        state.alt_dm = static_cast<uint16_t>((alt_m + 1000.0) * 10.0);
        return q > 0;
    }

    return false;
}

#ifdef ESP_PLATFORM
bool gnss_init_uart1() {
    uart_config_t cfg{};
    cfg.baud_rate = 115200;
    cfg.data_bits = UART_DATA_8_BITS;
    cfg.parity = UART_PARITY_DISABLE;
    cfg.stop_bits = UART_STOP_BITS_1;
    cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    if (uart_param_config(UART_NUM_1, &cfg) != ESP_OK) {
        return false;
    }
    if (uart_set_pin(UART_NUM_1, PIN_GPS_TX, PIN_GPS_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) != ESP_OK) {
        return false;
    }
    return uart_driver_install(UART_NUM_1, 2048, 0, 0, nullptr, 0) == ESP_OK;
}
#endif

} // namespace scooterlab
