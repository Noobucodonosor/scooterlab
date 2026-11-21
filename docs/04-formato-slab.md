# Specifica Formato Binario `.slab` v1 (`TASK-DATA-01`)

- **Riferimento ADR:** [`ADR-0004`](./adr/0004-pipeline-dati-telemetria-uns-automazione.md)
- **Implementazioni allineate:**
  - Python: [`tools/slab_codec.py`](../tools/slab_codec.py)
  - Firmware C++: [`firmware/include/slab_format.h`](../firmware/include/slab_format.h)

---

## 1. Obiettivi di Progetto

Il formato `.slab` (ScooterLab Binary Log) è progettato per la registrazione deterministica su microSD da microcontrollori ESP32-S3/C5:
- **Zero allocazioni dinamiche** lato firmware (`packed struct`, little-endian).
- **Integrità verificabile:** CRC32 indipendente sia sull'header (32 byte) sia sull'intero payload record (footer da 8 byte).
- **Estendibilità per livello:** supporta `BUILD_LEVEL` 0 (IMU + GPS), 1 (RPM/Speed/Gas) e 2 (CAN/OBD + Sospensioni) tramite record tipizzati.

---

## 2. Layout del File (Little-Endian)

### A. File Header — 32 byte (`<4sBBHHHII8sI`)

| Offset | Tipo | Campo | Descrizione |
| :--- | :--- | :--- | :--- |
| `0` | `char[4]` | `magic` | Sempre `"SLAB"` (`0x53 0x4C 0x41 0x42`) |
| `4` | `uint8` | `version` | Versione formato (`1`) |
| `5` | `uint8` | `build_level` | Livello montaggio (`0`, `1` o `2`) |
| `6` | `uint16` | `imu_hz` | Frequenza nominale campionamento IMU (es. `100` o `1000` Hz) |
| `8` | `uint16` | `gps_hz` | Frequenza nominale GNSS (es. `1`, `5` o `10` Hz) |
| `10` | `uint16` | `flags` | Bitfield (bit 0: ISPU abilitato, bit 1: CAN attivo) |
| `12` | `uint32` | `start_epoch_s` | Timestamp UTC inizio sessione (secondi Unix, `0` se senza fix iniziale) |
| `16` | `uint32` | `record_count` | Numero totale di record nel file (`0` se chiuso in emergenza) |
| `20` | `uint8[8]` | `reserved` | Riservato a uso futuro (tutti `0x00`) |
| `28` | `uint32` | `header_crc32` | CRC32 (IEEE 802.3) dei primi 28 byte |

### B. Sequenza di Record (Header 4 byte + Payload)

Ogni record inizia con un mini-header da 4 byte (`<BBH`):
- `rec_type` (`uint8`): `1` = IMU, `2` = GPS, `3` = CAN/OBD
- `rec_len` (`uint8`): lunghezza payload in byte
- `reserved` (`uint16`): `0`

#### Record Tipo `1` — IMU (`20 byte`, `<Ihhhhhhhh`)
| Campo | Tipo | Unità / Scala |
| :--- | :--- | :--- |
| `t_ms` | `uint32` | Millisecondi dall'inizio sessione |
| `ax_mg, ay_mg, az_mg` | `int16 × 3` | Accelerazione in milli-g (`1000` = 1 g) |
| `gx_ddps, gy_ddps, gz_ddps` | `int16 × 3` | Velocità angolare in deci-gradi/s (`10` = 1 °/s) |
| `roll_cdeg, pitch_cdeg` | `int16 × 2` | Angoli di piega e beccheggio in centi-gradi (`100` = 1,00 °) |

#### Record Tipo `2` — GPS (`20 byte`, `<IiiHHBBH`)
| Campo | Tipo | Unità / Scala |
| :--- | :--- | :--- |
| `t_ms` | `uint32` | Millisecondi dall'inizio sessione |
| `lat_e7, lon_e7` | `int32 × 2` | Gradi decimali × `10^7` |
| `speed_cms` | `uint16` | Velocità reale in cm/s (`1000` = 10 m/s = 36 km/h) |
| `alt_dm` | `uint16` | Altitudine in decimetri con offset `+1000 m` (`10000` = 0 m slm) |
| `sats` | `uint8` | Numero satelliti agganciati |
| `fix` | `uint8` | `0` = no fix, `2` = 2D, `3` = 3D |
| `hdop_x10` | `uint16` | HDOP × 10 |

#### Record Tipo `3` — CAN / TWAI (`20 byte`, `<IIB3x8s`, ADR-0007)
| Campo | Tipo | Unità / Scala |
| :--- | :--- | :--- |
| `t_ms` | `uint32` | Millisecondi dall'inizio sessione |
| `can_id` | `uint32` | Identificativo frame CAN (11 o 29 bit) |
| `dlc` | `uint8` | Lunghezza payload CAN (`0..8`) |
| `reserved` | `uint8[3]` | Padding allineamento a 0 |
| `data` | `uint8[8]` | Byte payload CAN |

#### Record Tipo `4` — Health Elettrico/Termico (`8 byte`, `<IHh`, ADR-0007)
| Campo | Tipo | Unità / Scala |
| :--- | :--- | :--- |
| `t_ms` | `uint32` | Millisecondi dall'inizio sessione |
| `vbat_mv` | `uint16` | Tensione batteria/regolatore `IGN_SENSE` in mV |
| `temp_dc` | `int16` | Temperatura interna scatola IP65 in deci-°C (`315` = 31,5 °C) |

### C. File Footer — 8 byte (`<4sI`)
- `magic`: `"END!"` (`0x45 0x4E 0x44 0x21`)
- `payload_crc32`: CRC32 (IEEE 802.3) di tutti i byte dei record (dal byte 32 fino al footer escluso).
