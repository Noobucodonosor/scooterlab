#pragma once
/**
 * ScooterLab Session Naming & Upload Sync Tracker (ADR-0006).
 * Prevents overwriting `.slab` files across ignition cycles and avoids re-uploading
 * sessions already confirmed with HTTP 200.
 */

#include <stddef.h>

namespace scooterlab {

bool next_session_path(const char *sessions_dir,
                       char *out_path,
                       size_t out_path_len,
                       char *out_name,
                       size_t out_name_len);

bool is_session_uploaded(const char *slab_path);
bool mark_session_uploaded(const char *slab_path);

} // namespace scooterlab
