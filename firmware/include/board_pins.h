#pragma once
/**
 * ScooterLab ESP32-S3 Default Pinout (ADR-0002 / ADR-0006 / docs/bom-rev2-2026.md).
 * Provides fallback definitions for pure `idf.py build` when PlatformIO build_flags are absent.
 */

#ifndef PIN_SPI_SCK
#define PIN_SPI_SCK 12
#endif
#ifndef PIN_SPI_MOSI
#define PIN_SPI_MOSI 11
#endif
#ifndef PIN_SPI_MISO
#define PIN_SPI_MISO 13
#endif
#ifndef PIN_CS_IMU
#define PIN_CS_IMU 10
#endif
#ifndef PIN_INT_IMU
#define PIN_INT_IMU 9
#endif
#ifndef PIN_SD_SCK
#define PIN_SD_SCK 36
#endif
#ifndef PIN_SD_MOSI
#define PIN_SD_MOSI 35
#endif
#ifndef PIN_SD_MISO
#define PIN_SD_MISO 37
#endif
#ifndef PIN_CS_SD
#define PIN_CS_SD 14
#endif
#ifndef PIN_GPS_RX
#define PIN_GPS_RX 18
#endif
#ifndef PIN_GPS_TX
#define PIN_GPS_TX 17
#endif
#ifndef PIN_IGN_SENSE
#define PIN_IGN_SENSE 4
#endif
#ifndef PIN_CAN_TX
#define PIN_CAN_TX 5
#endif
#ifndef PIN_CAN_RX
#define PIN_CAN_RX 6
#endif
#ifndef PIN_STATUS_LED
#define PIN_STATUS_LED 2
#endif
