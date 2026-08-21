# LBrightness

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner_light.svg">
  <img alt="LBrightness Banner" src="assets/banner_light.svg">
</picture>

[![Version](https://img.shields.io/github/v/release/LeanBitLab/adaptive-brightness-linux?label=Version&style=for-the-badge&color=7C4DFF)](https://github.com/LeanBitLab/adaptive-brightness-linux/releases/latest) [![Downloads](https://img.shields.io/github/downloads/LeanBitLab/adaptive-brightness-linux/total?style=for-the-badge&color=7C4DFF&label=Downloads)](https://github.com/LeanBitLab/adaptive-brightness-linux/releases) [![Stars](https://img.shields.io/github/stars/LeanBitLab/adaptive-brightness-linux?style=for-the-badge&color=7C4DFF)](https://github.com/LeanBitLab/adaptive-brightness-linux/stargazers) [![Sponsor](https://img.shields.io/badge/Sponsor-LeanBitLab-7C4DFF?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/LeanBitLab)

**LBrightness (`lbright`)** is a lightweight, ultra-efficient, intelligent auto-brightness system for Linux. Written in high-performance **Rust**, it automatically adjusts screen brightness based on time-of-day curves and Ambient Light Sensors (ALS), learning from your manual adjustments seamlessly.

Built for microsecond-fast direct kernel `sysfs` I/O, robust external monitor DDC/CI control via `ddcutil`, and sub-5MB background memory footprint with zero runtime crashes.

---

## 🚀 Key Features

- **⚡ Direct Sysfs Hardware Control:** Reads and writes directly to `/sys/class/backlight/*` with zero subprocess overhead and microsecond latency.
- **🖥️ External Monitor Support (DDC/CI):** Communicates with external monitors via DDC/CI (VCP `0x10`) over an isolated worker thread with command timeouts.
- **🧠 Adaptive Learning:** Learns your preferred screen brightness when you make manual adjustments on internal panels.
- **📈 24-Hour Time Curves:** Smooth, linear interpolation wrapping seamlessly across midnight.
- **☀️ Ambient Light Sensor (ALS) Integration:** Smooths sensor readings with rolling average and configurable hysteresis to eliminate screen jitter.
- **⌨️ Interactive Terminal UI (TUI):** Built-in ANSI line-based menu to view live status, edit 24h curves, toggle pause, and rescan devices over SSH or local terminal.
- **🪶 Zero-Overhead Background Daemon:** Uses a predictable 100ms synchronous tick loop with **< 4MB RSS** and 0.0% idle CPU.
- **🔄 Non-Destructive Migration:** Import legacy `profiles.conf` into the new structured INI format with `lbright migrate [--dry-run]`.

---

## ⌨️ CLI & Subcommands

```bash
# View live system status, detected displays, brightness, and sensor metrics
lbright status

# Open interactive terminal menu & curve editor
lbright tui

# Scan for internal panels and external DDC/CI displays
lbright scan

# Manually set brightness (0-100)
lbright set internal 60
lbright set ddc:1 50
lbright set ddc:serial=ABC123 45

# Pause or resume automatic adjustments
lbright pause 30m
lbright pause 1h
lbright pause indefinite
lbright pause off

# Import old profiles.conf into config.ini
lbright migrate --dry-run
lbright migrate

# Run background daemon manually (or via systemd)
lbright daemon --foreground
```

---

## 📦 Prerequisites & Installation

### Prerequisites
- `rust` & `cargo` (to build from source)
- `systemd` (optional, for user service)
- `ddcutil` (optional, required only for external DDC/CI monitors)

### Quick Install

```bash
git clone https://github.com/LeanBitLab/adaptive-brightness-linux.git
cd adaptive-brightness-linux
chmod +x install.sh
./install.sh
```

The installer builds the release binary, places `lbright` in `~/.local/bin/`, and sets up the `lbright.service` user unit.

### 🗑️ Uninstallation

```bash
./uninstall.sh
```

---

## 📂 Configuration & State Paths

- **Configuration:** `~/.config/lbrightness/config.ini`
- **State Directory:** `~/.local/state/lbrightness/`
- **Legacy Profiles:** `~/.config/auto-brightness/profiles.conf` (can be imported via `lbright migrate`)

---

## 🛡️ LeanBitLab Ecosystem

Check out our other projects: 👉 [LeanBitLab Projects](https://github.com/LeanBitLab#-current-projects)
