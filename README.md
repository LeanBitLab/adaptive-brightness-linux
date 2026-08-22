# LBrightness

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/banner_light.svg">
  <img alt="LBrightness Banner" src="assets/banner_light.svg">
</picture>

[![Version](https://img.shields.io/github/v/release/LeanBitLab/adaptive-brightness-linux?label=Version&style=for-the-badge&color=7C4DFF)](https://github.com/LeanBitLab/adaptive-brightness-linux/releases/latest) [![Stars](https://img.shields.io/github/stars/LeanBitLab/adaptive-brightness-linux?style=for-the-badge&color=7C4DFF)](https://github.com/LeanBitLab/adaptive-brightness-linux/stargazers) [![License: MIT](https://img.shields.io/badge/License-MIT-7C4DFF?style=for-the-badge)](LICENSE) [![Sponsor](https://img.shields.io/badge/Sponsor-LeanBitLab-7C4DFF?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/LeanBitLab)

**LBrightness (`lbright`)** is a lightweight, ultra-efficient, intelligent auto-brightness system for Linux. Written in high-performance **Rust**, it automatically adjusts screen brightness based on configurable time-of-day curves and Ambient Light Sensors (ALS), seamlessly learning your preferred levels when you make manual adjustments.

Built for microsecond-fast direct kernel `sysfs` I/O, robust external monitor DDC/CI control via `ddcutil`, and sub-5MB background memory footprint (< 4MB RSS typical) with zero idle CPU overhead.

<p align="center">
  <img src="docs/screenshots/1.png" alt="LBrightness Preview 1" width="48%">
  <img src="docs/screenshots/2.png" alt="LBrightness Preview 2" width="48%">
</p>

---

## 🚀 Key Features

- **⚡ Direct Sysfs Hardware Control:** Reads and writes directly to `/sys/class/backlight/*` with zero subprocess overhead and microsecond latency.
- **🖥️ External Monitor Support (DDC/CI):** Communicates with external monitors via DDC/CI (VCP `0x10`) over an isolated worker thread with non-blocking timeouts to prevent system freezes.
- **🧠 Adaptive Learning:** Learns your preferred screen brightness when you make manual adjustments on internal panels.
- **📈 24-Hour Time Curves:** Smooth, linear interpolation wrapping seamlessly across midnight.
- **☀️ Ambient Light Sensor (ALS) Integration:** Smooths sensor readings with rolling averages and configurable hysteresis to eliminate screen brightness jitter.
- **⌨️ Interactive Terminal UI (TUI):** Built-in ANSI menu (`lbright tui`) to view live status, add/edit/delete curve points, test time targets, toggle ALS, pause/resume, and rescan displays.
- **🪶 Zero-Overhead Background Daemon:** Uses a predictable 100ms synchronous tick loop with **< 4MB RSS** and 0.0% idle CPU.
- **🔄 Non-Destructive Migration:** Import legacy `profiles.conf` into the new structured INI format with `lbright migrate [--dry-run]`.
- **🔒 Advisory Config Locking:** Prevents race conditions and write collisions between daemon learning and interactive configuration edits.

---

## 📦 Prerequisites & Hardware Permissions

### Prerequisites
- **Rust & Cargo** (required to build from source): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **systemd** (optional, recommended for user background service management)
- **ddcutil** (optional, required only for external DDC/CI monitors): `sudo apt install ddcutil i2c-tools` (or equivalent for your distribution)

### Hardware Permissions Setup

To allow `lbright` to control internal backlights and external DDC/CI monitors without requiring root privileges:

```bash
# Add your user to the video and i2c groups
sudo usermod -aG video,i2c $USER

# Ensure the i2c-dev kernel module is loaded for external monitor control
sudo modprobe i2c-dev
echo "i2c-dev" | sudo tee /etc/modules-load.d/i2c-dev.conf
```
> [!NOTE]
> Log out and log back in (or restart) for group permission changes to take effect.

---

## 🛠️ Installation & Setup

### Quick Install (Automated)

Clone the repository and run the included installer script:

```bash
git clone https://github.com/LeanBitLab/adaptive-brightness-linux.git
cd adaptive-brightness-linux
chmod +x install.sh
./install.sh
```

The installer will:
1. Compile the optimized release binary (`cargo build --release`).
2. Install `lbright` to `~/.local/bin/lbright`.
3. Install and harden `lbright.service` into `~/.config/systemd/user/`.
4. Gracefully stop any legacy daemon and start `lbright.service`.

### Debian / Ubuntu (`.deb` Package)

To build and install a standard Debian package on Debian, Ubuntu, Linux Mint, or Pop!_OS:

```bash
# Build the package
./build-deb.sh

# Install the generated .deb package
sudo dpkg -i lbright_*.deb

# Enable and start the background service
systemctl --user enable --now lbright.service
```

### Manual Build & Installation

```bash
# Build release binary
cargo build --release

# Copy binary to user path
install -Dm755 target/release/lbright "$HOME/.local/bin/lbright"

# Install systemd user service
install -Dm644 lbright.service "$HOME/.config/systemd/user/lbright.service"

# Reload and start service
systemctl --user daemon-reload
systemctl --user enable --now lbright.service
```

---

## ⚙️ Service Management

Manage the background daemon using standard `systemctl` commands:

```bash
# Check daemon status and resource usage
systemctl --user status lbright.service

# Restart the daemon
systemctl --user restart lbright.service

# Stop the daemon
systemctl --user stop lbright.service

# View real-time daemon logs
journalctl --user -u lbright.service -f
```

---

## ⌨️ CLI Subcommands & Usage

`lbright` provides a full suite of CLI subcommands for control, status inspection, and configuration.

```
lbright <SUBCOMMAND> [OPTIONS]
```

### Subcommand Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `status` | Display detected hardware, current brightness, ALS sensor metrics, and pause state | `lbright status` |
| `tui` | Launch the interactive ANSI terminal menu and curve editor | `lbright tui` |
| `scan` | Scan and list all internal backlight panels and external DDC/CI monitors | `lbright scan` |
| `set <device> <0-100>` | Manually set target brightness percentage on a specific device | `lbright set internal 65` |
| `pause <duration\|off>` | Temporarily or indefinitely pause automatic adjustments | `lbright pause 30m` |
| `migrate [--dry-run]` | Import legacy `~/.config/auto-brightness/profiles.conf` into `config.ini` | `lbright migrate --dry-run` |
| `daemon [--foreground]` | Run background daemon process (used by systemd) | `lbright daemon --foreground` |
| `version` | Print current `lbright` version | `lbright version` |
| `help` | Print help and CLI options | `lbright help` |

### Device Identifier Syntax (for `set` and `config.ini`)

- `internal`: Primary internal backlight panel (`/sys/class/backlight/*`).
- `internal:<name>`: Specific internal panel (e.g. `internal:intel_backlight`, `internal:amdgpu_bl0`).
- `ddc:default`: First detected external DDC/CI display.
- `ddc:<index>`: Specific DDC display index (e.g. `ddc:1`, `ddc:2`).
- `ddc:bus=<bus>`: Specific I2C bus number (e.g. `ddc:bus=7`).
- `ddc:serial=<sn>`: Specific monitor serial number (e.g. `ddc:serial=ABC123456`).
- `ddc:model=<model>`: Specific monitor model name (e.g. `ddc:model=DELL_U2720Q`).

### Examples

```bash
# View live status
lbright status

# Manually set internal screen brightness to 60%
lbright set internal 60

# Set external DDC monitor #1 to 45%
lbright set ddc:1 45

# Pause adjustments for 1 hour (e.g. during gaming or movie playback)
lbright pause 1h

# Resume adjustments immediately
lbright pause off

# Check current pause timer status
lbright pause status

# Preview migration from old profiles.conf
lbright migrate --dry-run
```

---

## 🖥️ Interactive Terminal UI (`lbright tui`)

Run `lbright tui` from any terminal or SSH session to access an interactive management console:

```
==========================================
       LBrightness Control Menu
==========================================

--- Main Menu --- [State: Active]
1) Live Status & Devices
2) Edit Internal Brightness Curve
3) Edit External Display Profiles
4) Toggle Ambient Sensor (Currently: Disabled)
5) Pause / Resume Adjustments
6) Rescan Displays
7) Migrate Old Config (profiles.conf)
8) Reload Daemon
9) Exit
```

- **Interactive Curve Editor:** Add, edit, remove, and simulate target brightness for specific timestamps (`HHMM`).
- **Safe Advisory Locks:** All edits made through the TUI automatically acquire advisory file locks, ensuring background learning won't overwrite your changes.

---

## 🖥️ External Display Setup (DDC/CI) & Troubleshooting

`lbright` controls external monitors using the industry-standard **DDC/CI** (Display Data Channel Command Interface) protocol via `ddcutil`.

### 1. Requirements for External Displays

* **Direct Digital Connection (Required):**
  * Connect using direct **HDMI-to-HDMI**, **DisplayPort-to-DisplayPort**, **USB-C (DP Alt Mode)**, or **DVI-D**.
  > [!WARNING]
  > **VGA to HDMI / HDMI to VGA adapters do NOT work.** Active and passive analog VGA converters block bidirectional I2C communication on slave address `0x37`, preventing software brightness adjustment.
* **Monitor OSD Menu Configuration:**
  * Open your physical monitor's built-in On-Screen Display (OSD) menu using its front or bottom buttons.
  * Navigate to **Settings** / **System** / **OSD Setup** / **Miscellaneous**.
  * Ensure **DDC/CI** is toggled to **"On"** or **"Enabled"**.
* **Software Prerequisites & Permissions:**
  ```bash
  # Install ddcutil and i2c-tools
  sudo apt install -y ddcutil i2c-tools

  # Add your user to the i2c group
  sudo usermod -aG i2c $USER

  # Ensure kernel i2c-dev module is loaded
  sudo modprobe i2c-dev
  echo "i2c-dev" | sudo tee /etc/modules-load.d/i2c-dev.conf
  ```

### 2. Verify External Display Detection

Test if your monitor responds to DDC/CI commands:

```bash
# 1. Direct hardware check
ddcutil detect

# 2. LBrightness hardware scan
lbright scan

# 3. Test changing brightness on external display #1 to 50%
lbright set ddc:1 50
```

### 3. External Display Troubleshooting

| Issue / Error Message | Cause | Solution |
| :--- | :--- | :--- |
| `Monitor does not support DDC/CI (address 0x37 unresponsive)` | DDC/CI disabled in monitor menu or blocked by video adapter. | 1. Enable DDC/CI in monitor physical OSD menu.<br>2. Replace VGA converter dongles with direct HDMI, DisplayPort, or DVI cables. |
| `Permission denied` opening `/dev/i2c-*` | Current user is not in `i2c` group. | Run `sudo usermod -aG i2c $USER`, then log out and log back in (or run `newgrp i2c`). |
| External monitor not updating in background daemon | Display section disabled or daemon needs rescan. | Run `lbright scan` or open `lbright tui` -> *Edit External Display Profiles* to ensure the profile is enabled. |

---

## 🔧 Configuration Reference (`config.ini`)

The configuration file is located at `~/.config/lbrightness/config.ini`. It uses an INI structure with a `[general]` section and individual device curve sections.

### Sample Configuration

```ini
# LBrightness Configuration
version = 2

[general]
interval_min = 15
ambient = false
ambient_poll_sec = 5
ambient_average = 3
ambient_hysteresis_pct = 3
fade_internal = true
fade_external = false
learn_internal = true
learn_external = false
min_internal = 5
max_internal = 100
min_external = 0
max_external = 100
ddc_rescan_min = 5
ddc_cooldown_sec = 10
ddc_set_timeout_sec = 5
ddc_detect_timeout_sec = 10

[internal]
enabled = true
point = 00:00:18
point = 07:00:45
point = 12:00:65
point = 19:00:55
point = 23:00:25

[ddc:default]
enabled = true
point = 00:00:18
point = 07:00:45
point = 12:00:65
point = 19:00:55
point = 23:00:25
```

### Settings Breakdown

#### `[general]` Settings

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `interval_min` | Integer | `15` | Periodic interval (in minutes) for recalculating time curves. |
| `ambient` | Boolean | `false` | Enable or disable Ambient Light Sensor (ALS) integration. |
| `ambient_poll_sec` | Integer | `5` | Sensor reading interval in seconds. |
| `ambient_average` | Integer | `3` | Number of recent sensor samples used for rolling average smoothing. |
| `ambient_hysteresis_pct`| Integer | `3` | Deadband percentage required before ALS triggers a brightness update (eliminates jitter). |
| `fade_internal` | Boolean | `true` | Enables smooth multi-step brightness fading on internal sysfs panels. |
| `fade_external` | Boolean | `false` | Multi-step fading on DDC displays (disabled by default due to I2C communication bus latency). |
| `learn_internal` | Boolean | `true` | Automatically adjust 24h curve points when you change internal brightness manually. |
| `learn_external` | Boolean | `false` | Automatically learn adjustments on external DDC displays. |
| `min_internal` | Integer (0-100) | `5` | Minimum brightness floor for internal panel (prevents accidental black screen). |
| `max_internal` | Integer (0-100) | `100` | Maximum brightness ceiling for internal panel. |
| `min_external` | Integer (0-100) | `0` | Minimum brightness floor for external displays. |
| `max_external` | Integer (0-100) | `100` | Maximum brightness ceiling for external displays. |
| `ddc_rescan_min` | Integer | `5` | Periodic interval (in minutes) to rescan for attached/detached external monitors. |
| `ddc_cooldown_sec` | Integer | `10` | Backoff cooldown period if a DDC communication error occurs. |
| `ddc_set_timeout_sec` | Integer | `5` | Maximum execution timeout (in seconds) for `ddcutil setvcp` commands. |
| `ddc_detect_timeout_sec`| Integer | `10` | Maximum execution timeout (in seconds) for `ddcutil detect` scans. |

#### Device Curve Sections (`[<device_id>]`)

- `enabled = true|false`: Enables or disables brightness management for this display.
- `point = HH:MM:PERCENT`: Curve control point mapping 24-hour time to brightness percentage (`0-100`). `lbright` uses smooth linear interpolation between adjacent points across midnight.

---

## 📂 Configuration Paths & Environment Overrides

| Resource | Default Path | Environment Override |
| :--- | :--- | :--- |
| **Active Config** | `~/.config/lbrightness/config.ini` | `LBRIGHT_CONFIG_PATH` |
| **State Directory** | `~/.local/state/lbrightness/` | `LBRIGHT_STATE_DIR` |
| **Legacy Config** | `~/.config/auto-brightness/profiles.conf` | `LBRIGHT_LEGACY_CONFIG_PATH` |

---

## 🔄 Legacy Migration & Rollback

### Migrating from Python Auto-Brightness

If you previously used the Python version of `auto-brightness`, import your existing profiles and time curves into `lbright`:

```bash
# Preview the converted configuration without writing
lbright migrate --dry-run

# Perform non-destructive migration
lbright migrate
```
Your original `~/.config/auto-brightness/profiles.conf` will remain untouched.

### Rollback Guide

If you need to revert to the legacy Python service during testing:

```bash
# Disable lbright and enable legacy python service
systemctl --user disable --now lbright.service
systemctl --user enable --now auto-brightness.service
```

To switch back to `lbright`:
```bash
systemctl --user disable --now auto-brightness.service
systemctl --user enable --now lbright.service
```

---

## 🗑️ Uninstallation

Run the uninstaller script to remove the binary and systemd service:

```bash
./uninstall.sh
```

To automatically delete configuration and state files without prompting:
```bash
./uninstall.sh -y
```

---

## 🛡️ LeanBitLab Ecosystem

Check out our other projects: 👉 [LeanBitLab Projects](https://github.com/LeanBitLab#-current-projects)

