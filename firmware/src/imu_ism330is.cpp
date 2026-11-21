#include "imu_ism330is.h"
#include "board_pins.h"

#ifdef ESP_PLATFORM
#include "driver/spi_master.h"
#endif

namespace scooterlab {

int16_t ism330is_raw_to_mg_8g(int16_t raw) {
    // 0.244 mg/LSB -> (raw * 244) / 1000
    return static_cast<int16_t>((static_cast<int32_t>(raw) * 244) / 1000);
}

int16_t ism330is_raw_to_ddps_1000dps(int16_t raw) {
    // 35 mdps/LSB = 0.35 ddps/LSB -> (raw * 35) / 100
    return static_cast<int16_t>((static_cast<int32_t>(raw) * 35) / 100);
}

static int16_t read_le16(const uint8_t *p) {
    return static_cast<int16_t>(static_cast<uint16_t>(p[0]) | (static_cast<uint16_t>(p[1]) << 8));
}

void ism330is_parse_burst_12b(const uint8_t raw[12], uint32_t t_ms, slab_imu_rec_t &out) {
    out.t_ms = t_ms;
    out.gx_ddps = ism330is_raw_to_ddps_1000dps(read_le16(raw + 0));
    out.gy_ddps = ism330is_raw_to_ddps_1000dps(read_le16(raw + 2));
    out.gz_ddps = ism330is_raw_to_ddps_1000dps(read_le16(raw + 4));
    out.ax_mg = ism330is_raw_to_mg_8g(read_le16(raw + 6));
    out.ay_mg = ism330is_raw_to_mg_8g(read_le16(raw + 8));
    out.az_mg = ism330is_raw_to_mg_8g(read_le16(raw + 10));
    out.roll_cdeg = 0;
    out.pitch_cdeg = 0;
}

#ifdef ESP_PLATFORM
static spi_device_handle_t s_imu_dev = nullptr;

static bool imu_write_reg(uint8_t reg, uint8_t val) {
    if (s_imu_dev == nullptr) {
        return false;
    }
    uint8_t tx[2] = {static_cast<uint8_t>(reg & 0x7Fu), val};
    spi_transaction_t t{};
    t.length = 16;
    t.tx_buffer = tx;
    return spi_device_polling_transmit(s_imu_dev, &t) == ESP_OK;
}

static bool imu_read_regs(uint8_t reg, uint8_t *rx_out, size_t len) {
    if (s_imu_dev == nullptr || len > 16) {
        return false;
    }
    uint8_t tx[17]{};
    uint8_t rx[17]{};
    tx[0] = static_cast<uint8_t>(reg | 0x80u);
    spi_transaction_t t{};
    t.length = (len + 1) * 8;
    t.tx_buffer = tx;
    t.rx_buffer = rx;
    if (spi_device_polling_transmit(s_imu_dev, &t) != ESP_OK) {
        return false;
    }
    for (size_t i = 0; i < len; ++i) {
        rx_out[i] = rx[i + 1];
    }
    return true;
}

bool ism330is_init_spi2() {
    spi_bus_config_t buscfg{};
    buscfg.mosi_io_num = PIN_SPI_MOSI;
    buscfg.miso_io_num = PIN_SPI_MISO;
    buscfg.sclk_io_num = PIN_SPI_SCK;
    buscfg.quadwp_io_num = -1;
    buscfg.quadhd_io_num = -1;
    if (spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_CH_AUTO) != ESP_OK) {
        return false;
    }

    spi_device_interface_config_t devcfg{};
    devcfg.clock_speed_hz = 10 * 1000 * 1000;
    devcfg.mode = 3;
    devcfg.spics_io_num = PIN_CS_IMU;
    devcfg.queue_size = 2;
    if (spi_bus_add_device(SPI2_HOST, &devcfg, &s_imu_dev) != ESP_OK) {
        return false;
    }

    uint8_t who = 0;
    if (!imu_read_regs(ISM330IS_REG_WHO_AM_I, &who, 1) || who != ISM330IS_WHO_AM_I_VAL) {
        return false;
    }
    // 104 Hz ODR, +/-8g XL (0x4C) and +/-1000 dps Gyro (0x48)
    return imu_write_reg(ISM330IS_REG_CTRL1_XL, 0x4C) && imu_write_reg(ISM330IS_REG_CTRL2_G, 0x48);
}

bool ism330is_read_sample(uint32_t t_ms, slab_imu_rec_t &out) {
    uint8_t burst[12]{};
    if (!imu_read_regs(ISM330IS_REG_OUTX_L_G, burst, sizeof(burst))) {
        return false;
    }
    ism330is_parse_burst_12b(burst, t_ms, out);
    return true;
}
#endif

} // namespace scooterlab
