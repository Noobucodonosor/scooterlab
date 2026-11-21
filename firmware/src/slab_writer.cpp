#include "slab_writer.h"

#include <string.h>
#include <unistd.h>

namespace scooterlab {

uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) {
            uint32_t mask = -(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return crc;
}

uint32_t crc32_ieee(const uint8_t *data, size_t len) {
    return ~crc32_update(0xFFFFFFFFu, data, len);
}

SlabWriter::~SlabWriter() {
    if (fp_ != nullptr) {
        close_safe();
    }
}

bool SlabWriter::open(const char *path,
                      uint8_t build_level,
                      uint16_t imu_hz,
                      uint16_t gps_hz,
                      uint16_t flags,
                      uint32_t start_epoch_s) {
    if (fp_ != nullptr || path == nullptr) {
        return false;
    }

    fp_ = fopen(path, "wb+");
    if (fp_ == nullptr) {
        return false;
    }

    memset(&header_, 0, sizeof(header_));
    memcpy(header_.magic, "SLAB", 4);
    header_.version = SLAB_VERSION;
    header_.build_level = build_level;
    header_.imu_hz = imu_hz;
    header_.gps_hz = gps_hz;
    header_.flags = flags;
    header_.start_epoch_s = start_epoch_s;
    header_.record_count = 0;
    header_.header_crc32 = crc32_ieee(reinterpret_cast<const uint8_t *>(&header_), 28);

    record_count_ = 0;
    payload_crc_ = 0xFFFFFFFFu;
    buf_pos_ = 0;

    if (fwrite(&header_, sizeof(header_), 1, fp_) != 1) {
        fclose(fp_);
        fp_ = nullptr;
        return false;
    }
    return true;
}

bool SlabWriter::flush_buffer() {
    if (fp_ == nullptr) {
        return false;
    }
    if (buf_pos_ == 0) {
        return true;
    }
    const size_t expected = buf_pos_;
    const size_t written = fwrite(buf_, 1, expected, fp_);
    buf_pos_ = 0;
    return written == expected;
}

bool SlabWriter::write_buffered(const uint8_t *data, size_t len) {
    size_t offset = 0;
    while (offset < len) {
        const size_t space = kBlockBufSize - buf_pos_;
        const size_t chunk = (len - offset) < space ? (len - offset) : space;
        memcpy(buf_ + buf_pos_, data + offset, chunk);
        buf_pos_ += chunk;
        offset += chunk;
        if (buf_pos_ == kBlockBufSize) {
            if (fwrite(buf_, 1, kBlockBufSize, fp_) != kBlockBufSize) {
                buf_pos_ = 0;
                return false;
            }
            buf_pos_ = 0;
        }
    }
    return true;
}

bool SlabWriter::write_record(uint8_t rec_type, const void *payload, uint8_t len) {
    if (fp_ == nullptr || payload == nullptr) {
        return false;
    }

    slab_rec_hdr_t rh{};
    rh.rec_type = rec_type;
    rh.rec_len = len;
    rh.reserved = 0;

    if (!write_buffered(reinterpret_cast<const uint8_t *>(&rh), sizeof(rh))) {
        return false;
    }
    if (!write_buffered(reinterpret_cast<const uint8_t *>(payload), len)) {
        return false;
    }

    payload_crc_ = crc32_update(payload_crc_, reinterpret_cast<const uint8_t *>(&rh), sizeof(rh));
    payload_crc_ = crc32_update(payload_crc_, reinterpret_cast<const uint8_t *>(payload), len);
    record_count_++;
    return true;
}

bool SlabWriter::write_imu(const slab_imu_rec_t &rec) {
    return write_record(SLAB_REC_IMU, &rec, sizeof(rec));
}

bool SlabWriter::write_gps(const slab_gps_rec_t &rec) {
    return write_record(SLAB_REC_GPS, &rec, sizeof(rec));
}

bool SlabWriter::close_safe() {
    if (fp_ == nullptr) {
        return false;
    }

    bool ok = true;

    // 0. Flush 4 KB block buffer before appending footer
    if (!flush_buffer()) {
        ok = false;
    }

    // 1. Append footer with finalized payload CRC32
    slab_footer_t footer{};
    memcpy(footer.magic, "END!", 4);
    footer.payload_crc32 = ~payload_crc_;
    if (fwrite(&footer, sizeof(footer), 1, fp_) != 1) {
        ok = false;
    }

    // 2. Patch header with final record_count and recomputed header CRC32
    header_.record_count = record_count_;
    header_.header_crc32 = crc32_ieee(reinterpret_cast<const uint8_t *>(&header_), 28);
    if (fseek(fp_, 0, SEEK_SET) != 0 || fwrite(&header_, sizeof(header_), 1, fp_) != 1) {
        ok = false;
    }

    // 3. Flush stdio buffers and fsync underlying storage before hold-up cap drains
    if (fflush(fp_) != 0) {
        ok = false;
    }
    int fd = fileno(fp_);
    if (fd >= 0 && fsync(fd) != 0) {
        ok = false;
    }

    if (fclose(fp_) != 0) {
        ok = false;
    }
    fp_ = nullptr;
    return ok;
}

} // namespace scooterlab
