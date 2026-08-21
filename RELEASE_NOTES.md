# Release Notes - LBrightness 0.1.0-rc1

**Release Tag:** `v0.1.0-rc1`  
**Status:** Release Candidate 1 (RC1)

---

## 🌟 Highlights

- **Complete Rust Rewrite (`lbright`):** Core background daemon and CLI rewritten in 100% pure standard library Rust, reducing background memory consumption from **~80MB to 2.5MB RSS** (< 5MB typical) with zero idle CPU overhead.
- **Direct Sysfs Kernel I/O:** Fast direct reading and writing to `/sys/class/backlight/*` with microsecond latency and clear `video` group permissions diagnostics.
- **External Monitor Support (DDC/CI):** Isolated background worker thread communicates with external monitors via DDC/CI (VCP `0x10`) through `ddcutil` with strict execution timeouts (5s set, 10s detect) to prevent hangs.
- **Interactive Line-Based TUI:** Fast, zero-dependency ANSI menu (`lbright tui`) to inspect live status, edit 24h curves, toggle ALS, pause/resume, and rescan displays.
- **Non-Destructive Migration Engine:** `lbright migrate [--dry-run]` imports existing `~/.config/auto-brightness/profiles.conf` into structured `~/.config/lbrightness/config.ini` without modifying the original configuration.
- **Advisory Config Locking:** Prevents write collisions between background daemon learning and interactive TUI saves.
- **Systemd User Service Hardening:** `lbright.service` configured with `NoNewPrivileges=true` and `PrivateTmp=true`.

---

## 🚦 Stable Promotion Gates (24-Hour Soak)

`lbright 0.1.0-rc1` will be promoted to `0.1.0 stable` upon satisfying the following soak criteria:
1. Continuous 24-hour daemon run with no panics, coredumps, or restart loops.
2. Flat RSS memory curve (< 5MB) without sustained growth.
3. Idle CPU remaining near zero.
4. Clean suspend/resume recovery and external monitor hotplug rescan.
5. Successful real DDC/CI monitor adjustment (or external DDC support clearly designated as beta if hardware is unavailable).

---

## 🔄 Rollback Instructions

The legacy Python implementation files (`auto-brightness-daemon.py`, `gui.py`) and configuration (`profiles.conf`) are fully preserved during the RC testing period.

To roll back to the legacy Python service:
```bash
systemctl --user disable --now lbright.service
systemctl --user enable --now auto-brightness.service
```

To restore the `lbright` service:
```bash
systemctl --user disable --now auto-brightness.service
systemctl --user enable --now lbright.service
```
