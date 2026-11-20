"""ScooterLab binary telemetry codec (.slab v1).

Aligned byte-for-byte with `firmware/include/slab_format.h` and `docs/04-formato-slab.md`.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

MAGIC_HEADER = b"SLAB"
MAGIC_FOOTER = b"END!"
FORMAT_VERSION = 1

REC_IMU = 1
REC_GPS = 2
REC_CAN = 3

HEADER_BODY_FMT = "<4sBBHHHII8s"  # 28 bytes
HEADER_FMT = "<4sBBHHHII8sI"     # 32 bytes
REC_HDR_FMT = "<BBH"             # 4 bytes
IMU_FMT = "<Ihhhhhhhh"           # 20 bytes
GPS_FMT = "<IiiHHBBH"            # 20 bytes
FOOTER_FMT = "<4sI"              # 8 bytes

HEADER_SIZE = struct.calcsize(HEADER_FMT)
REC_HDR_SIZE = struct.calcsize(REC_HDR_FMT)
IMU_SIZE = struct.calcsize(IMU_FMT)
GPS_SIZE = struct.calcsize(GPS_FMT)
FOOTER_SIZE = struct.calcsize(FOOTER_FMT)


@dataclass(frozen=True)
class SlabHeader:
    version: int = FORMAT_VERSION
    build_level: int = 0
    imu_hz: int = 100
    gps_hz: int = 5
    flags: int = 0
    start_epoch_s: int = 0
    record_count: int = 0


@dataclass(frozen=True)
class ImuRecord:
    t_ms: int
    ax_mg: int
    ay_mg: int
    az_mg: int
    gx_ddps: int
    gy_ddps: int
    gz_ddps: int
    roll_cdeg: int
    pitch_cdeg: int


@dataclass(frozen=True)
class GpsRecord:
    t_ms: int
    lat_e7: int
    lon_e7: int
    speed_cms: int
    alt_dm: int
    sats: int
    fix: int
    hdop_x10: int


def write_slab(
    path: Path | str,
    header: SlabHeader,
    imu_records: Iterable[ImuRecord],
    gps_records: Iterable[GpsRecord],
) -> Path:
    """Serialize header + IMU/GPS records into a CRC32-verified `.slab` v1 file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = bytearray()
    count = 0

    for r in imu_records:
        payload.extend(struct.pack(REC_HDR_FMT, REC_IMU, IMU_SIZE, 0))
        payload.extend(
            struct.pack(
                IMU_FMT,
                r.t_ms,
                r.ax_mg,
                r.ay_mg,
                r.az_mg,
                r.gx_ddps,
                r.gy_ddps,
                r.gz_ddps,
                r.roll_cdeg,
                r.pitch_cdeg,
            )
        )
        count += 1

    for g in gps_records:
        payload.extend(struct.pack(REC_HDR_FMT, REC_GPS, GPS_SIZE, 0))
        payload.extend(
            struct.pack(
                GPS_FMT,
                g.t_ms,
                g.lat_e7,
                g.lon_e7,
                g.speed_cms,
                g.alt_dm,
                g.sats,
                g.fix,
                g.hdop_x10,
            )
        )
        count += 1

    hdr_body = struct.pack(
        HEADER_BODY_FMT,
        MAGIC_HEADER,
        header.version,
        header.build_level,
        header.imu_hz,
        header.gps_hz,
        header.flags,
        header.start_epoch_s,
        count,
        b"\x00" * 8,
    )
    hdr_crc = zlib.crc32(hdr_body) & 0xFFFFFFFF
    payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
    footer = struct.pack(FOOTER_FMT, MAGIC_FOOTER, payload_crc)

    with path.open("wb") as fh:
        fh.write(hdr_body)
        fh.write(struct.pack("<I", hdr_crc))
        fh.write(payload)
        fh.write(footer)

    return path


def read_slab(path: Path | str) -> Tuple[SlabHeader, List[ImuRecord], List[GpsRecord]]:
    """Read and validate a `.slab` v1 binary telemetry file."""
    raw = Path(path).read_bytes()
    if len(raw) < HEADER_SIZE + FOOTER_SIZE:
        raise ValueError("File .slab troppo corto o corrotto")

    hdr_body = raw[:28]
    (
        magic,
        version,
        build_level,
        imu_hz,
        gps_hz,
        flags,
        start_epoch_s,
        record_count,
        _reserved,
        stored_hdr_crc,
    ) = struct.unpack(HEADER_FMT, raw[:HEADER_SIZE])

    if magic != MAGIC_HEADER:
        raise ValueError(f"Magic header non valido: {magic!r}")
    if version != FORMAT_VERSION:
        raise ValueError(f"Versione .slab non supportata: {version}")

    calc_hdr_crc = zlib.crc32(hdr_body) & 0xFFFFFFFF
    if calc_hdr_crc != stored_hdr_crc:
        raise ValueError("Header CRC32 mismatch")

    payload = raw[HEADER_SIZE:-FOOTER_SIZE]
    footer_magic, stored_payload_crc = struct.unpack(FOOTER_FMT, raw[-FOOTER_SIZE:])
    if footer_magic != MAGIC_FOOTER:
        raise ValueError(f"Magic footer non valido: {footer_magic!r}")

    calc_payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if calc_payload_crc != stored_payload_crc:
        raise ValueError("Payload CRC32 mismatch")

    imu_records: List[ImuRecord] = []
    gps_records: List[GpsRecord] = []
    offset = 0
    while offset < len(payload):
        if offset + REC_HDR_SIZE > len(payload):
            raise ValueError("Record header troncato")
        rec_type, rec_len, _ = struct.unpack_from(REC_HDR_FMT, payload, offset)
        offset += REC_HDR_SIZE
        if offset + rec_len > len(payload):
            raise ValueError("Record payload troncato")
        chunk = payload[offset : offset + rec_len]
        offset += rec_len

        if rec_type == REC_IMU and rec_len == IMU_SIZE:
            imu_records.append(ImuRecord(*struct.unpack(IMU_FMT, chunk)))
        elif rec_type == REC_GPS and rec_len == GPS_SIZE:
            gps_records.append(GpsRecord(*struct.unpack(GPS_FMT, chunk)))

    header = SlabHeader(
        version=version,
        build_level=build_level,
        imu_hz=imu_hz,
        gps_hz=gps_hz,
        flags=flags,
        start_epoch_s=start_epoch_s,
        record_count=record_count,
    )
    return header, imu_records, gps_records
