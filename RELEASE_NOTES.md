# Release Notes - LBrightness 2.0.0 (Rust Rewrite)

**Release Tag:** `v2.0.0`  
**Status:** Major Version 2.0 Stable Release

---

## 🌟 Highlights

- **Complete 2.0 Rust Architecture (`lbright`):** Core background daemon and CLI rewritten in 100% pure standard library Rust, reducing background memory consumption from **~80MB to < 3.5MB RSS** with 0.0% idle CPU overhead.
- **Direct Sysfs Kernel I/O:** Fast direct reading and writing to `/sys/class/backlight/*` with microsecond latency and zero subprocess spawning overhead.
- **External Monitor Support (DDC/CI):** Dedicated background worker thread communicates with external monitors via DDC/CI (VCP `0x10`) through `ddcutil` with strict non-blocking timeouts (5s set, 10s detect) to prevent desktop freezes.
- **Interactive ANSI Terminal UI:** Fast, zero-dependency ANSI menu (`lbright tui`) to inspect live status, interactively edit 24h curves, toggle ALS, pause/resume, and rescan displays.
- **Non-Destructive Migration Engine:** `lbright migrate [--dry-run]` imports existing `~/.config/auto-brightness/profiles.conf` into structured `~/.config/lbrightness/config.ini` without modifying the original configuration.
- **Advisory Config Locking:** Prevents write collisions between background daemon learning and interactive TUI saves.
- **Hardened Systemd User Service:** `lbright.service` configured with `NoNewPrivileges=true` and `PrivateTmp=true`.
- **Multi-Channel Packaging:** Full support for Debian package installation (`.deb`), automated user installer (`install.sh`), standalone precompiled tarballs, and source builds via Cargo.

---

## 📦 Release Assets

- `lbright_2.0.0_amd64.deb` — Debian/Ubuntu/Mint installable package
- `lbright-v2.0.0-x86_64-linux.tar.gz` — Standalone binary archive
- `SHA256SUMS.txt` — SHA256 checksums for package integrity verification
