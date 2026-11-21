/**
 * Host-side C++17 unit & cross-language test for ScooterLab firmware modules.
 * Generates a real `.slab` v1 binary file that is then verified by Python `tools/analyze.py`.
 */

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "config_nvs.h"
#include "gnss_ublox.h"
#include "imu_ism330is.h"
#include "power_monitor.h"
#include "session_manager.h"
#include "slab_writer.h"
#include "uploader.h"

int main(int argc, char **argv) {
    const char *out_path = (argc > 1) ? argv[1] : "/tmp/cpp_firmware_test.slab";

    // 1. Verify NVS security validation (ADR-0003 / EN 18031)
    scooterlab::NvsConfig bad_cfg{};
    strcpy(bad_cfg.wifi_ssid, "GarageWiFi");
    strcpy(bad_cfg.wifi_pass, "strong-pass");
    strcpy(bad_cfg.ingest_url, "http://192.168.1.50:8500/upload"); // cleartext must fail!
    strcpy(bad_cfg.bearer_token, "1234567890abcdef1234567890");
    assert(!scooterlab::validate_nvs_config(bad_cfg));

    scooterlab::NvsConfig good_cfg = bad_cfg;
    strcpy(good_cfg.ingest_url, "https://garage.local:8500/upload");
    assert(scooterlab::validate_nvs_config(good_cfg));

    // 2. Verify SYM Symphony ST 200i power/regulator classification (TASK-HW-03)
    assert(scooterlab::adc_mv_to_vbat_mv(2500) == 14250);
    assert(scooterlab::classify_vbat_mv(14250) == scooterlab::PowerState::CHARGING_OK);
    assert(scooterlab::classify_vbat_mv(15200) == scooterlab::PowerState::OVER_VOLTAGE);
    assert(scooterlab::classify_vbat_mv(12500) == scooterlab::PowerState::NOMINAL_IDLE);
    assert(scooterlab::classify_vbat_mv(11800) == scooterlab::PowerState::BATTERY_LOW);
    assert(scooterlab::should_trigger_safe_shutdown(4500));
    assert(!scooterlab::should_trigger_safe_shutdown(12600));

    // 3. Write a realistic `.slab` v1 binary session using firmware `SlabWriter`
    scooterlab::SlabWriter writer;
    assert(writer.open(out_path, /*build_level=*/0, /*imu_hz=*/50, /*gps_hz=*/5, 0, 1795143600u));

    for (int i = 0; i < 50 * 20; ++i) {
        double t = i / 50.0;
        double roll = (t > 6.0) ? (20.0 * sin(0.8 * (t - 6.0))) : 0.0;
        slab_imu_rec_t imu{};
        imu.t_ms = static_cast<uint32_t>(t * 1000.0);
        imu.ax_mg = (t < 8.0) ? 250 : 20;
        imu.ay_mg = static_cast<int16_t>(sin(roll * 3.14159 / 180.0) * 400.0);
        imu.az_mg = static_cast<int16_t>(1000.0 + 70.0 * sin(2.0 * 3.14159 * 8.0 * t));
        imu.roll_cdeg = static_cast<int16_t>(roll * 100.0);
        imu.pitch_cdeg = -100;
        assert(writer.write_imu(imu));
    }

    for (int j = 0; j < 5 * 20; ++j) {
        double t = j / 5.0;
        double speed_ms = (t < 1.0) ? 0.0 : fmin(16.0, (t - 1.0) * 2.8);
        slab_gps_rec_t gps{};
        gps.t_ms = static_cast<uint32_t>(t * 1000.0);
        gps.lat_e7 = 440000000 + j * 150;
        gps.lon_e7 = 90000000;
        gps.speed_cms = static_cast<uint16_t>(speed_ms * 100.0);
        gps.alt_dm = 10100;
        gps.sats = 10;
        gps.fix = 3;
        gps.hdop_x10 = 10;
        assert(writer.write_gps(gps));
    }

    slab_can_rec_t can{};
    can.t_ms = 10000;
    can.can_id = 0x18FEF100u;
    can.dlc = 4;
    can.data[0] = 0x1A;
    can.data[1] = 0x2B;
    assert(writer.write_can(can));

    slab_health_rec_t health{};
    health.t_ms = 10000;
    health.vbat_mv = 14350;
    health.temp_dc = 315;
    assert(writer.write_health(health));

    assert(writer.record_count() == 1102);
    assert(writer.close_safe());

    // 4. Verify host-mode uploader accepts the generated file
    auto up = scooterlab::upload_slab_https(good_cfg, out_path, "cpp_test.slab", nullptr);
    assert(up.ok && up.http_status == 200 && up.bytes_sent > 20000);

    // 5. Verify ISM330IS SPI burst parsing & scaling
    const uint8_t burst[12] = {0x64, 0x00, 0x00, 0x00, 0x9C, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10};
    slab_imu_rec_t parsed_imu{};
    scooterlab::ism330is_parse_burst_12b(burst, 500, parsed_imu);
    assert(parsed_imu.gx_ddps == 35);
    assert(parsed_imu.gz_ddps == -35);
    assert(parsed_imu.az_mg == 999);

    // 6. Verify u-blox NMEA checksum + RMC/GGA parsing
    slab_gps_rec_t nmea_gps{};
    const char *rmc = "$GNRMC,123519,A,4421.0000,N,00913.8000,E,19.44,084.4,211126,003.1,W*72";
    const char *gga = "$GNGGA,123519,4421.0000,N,00913.8000,E,1,10,1.1,120.0,M,46.9,M,,*58";
    assert(scooterlab::nmea_parse_line(rmc, 1000, nmea_gps));
    assert(scooterlab::nmea_parse_line(gga, 1000, nmea_gps));
    assert(nmea_gps.fix == 3 && nmea_gps.sats == 10 && nmea_gps.hdop_x10 == 11);
    assert(nmea_gps.lat_e7 == 443500000 && nmea_gps.speed_cms >= 995 && nmea_gps.speed_cms <= 1005);
    assert(!scooterlab::nmea_parse_line("$G,1,2,3,4,5*55", 1000, nmea_gps));

    // 7. Verify session naming & upload sync marker
    char sess_path[256];
    char sess_name[64];
    assert(scooterlab::next_session_path("/tmp", sess_path, sizeof(sess_path), sess_name, sizeof(sess_name)));
    assert(!scooterlab::is_session_uploaded(out_path));
    assert(scooterlab::mark_session_uploaded(out_path));
    assert(scooterlab::is_session_uploaded(out_path));
    remove("/tmp/cpp_firmware_test.slab.uploaded");

    printf("[C++ Firmware Test] PASS — generated %s (%zu bytes, 1102 records + drivers OK)\n",
           out_path, up.bytes_sent);
    return 0;
}
