# Adaptive Brightness for Linux

A lightweight, intelligent auto-brightness script for Linux that automatically adjusts your screen brightness based on the time of day and **learns from your manual adjustments**, similar to Android's adaptive brightness feature.

**Author**: LeanBitLab

## How It Works
- **Time-Based Profiles:** By default, brightness smoothly ramps up during sunrise, peaks during the day, and gracefully ramps down during sunset into the night.
- **Adaptive Learning:** The script runs in the background. If you manually change your screen brightness using your keyboard or desktop environment slider, the script detects your intervention using mathematical comparisons. It then **permanently saves** your newly preferred brightness to the currently active time block's profile!
- **Intelligent Verification:** Smart enough to distinguish between a manual adjustment and a system reboot or long sleep gap, ensuring your profiles aren't accidentally overwritten with stale data.
- **Granular Control:** Profiles run in 15-30 minute intervals, providing continuous, smooth transitions without shocking your eyes.
- **Hardware Agnostic:** Communicates directly with the Linux kernel's `/sys/class/backlight` using `brightnessctl`, which means it works seamlessly on GNOME, KDE Plasma, XFCE, Sway, Hyprland, and other window managers.

## Prerequisites
- `bash` (Default on almost all distros)
- `systemd` (Default on most distros)
- `brightnessctl` (Available in most Linux package managers)

Install `brightnessctl` if you haven't already:
```bash
# Debian/Ubuntu based systems
sudo apt update && sudo apt install brightnessctl

# Arch Linux
sudo pacman -S brightnessctl

# Fedora
sudo dnf install brightnessctl
```

## Installation
Clone this repository and run the install script:

```bash
git clone https://github.com/LeanBitLab/adaptive-brightness-linux.git
cd adaptive-brightness-linux
chmod +x install.sh
./install.sh
```

## Configuration
The installation creates a configuration file where it stores your learned profiles. You can explicitly manually edit it at:
`~/.config/auto-brightness/profiles.conf`

It uses a simple `HHMM=PERCENT` format with 15-30 minute intervals:
```text
# Morning ramp-up
0800=40
0830=45
0900=50
# Evening wind-down
1700=62
1800=55
1900=45
```

## Logs & Diagnostics
To see the script in action or debug what it is evaluating, you can view the logs at:
`~/.local/state/auto-brightness.log`

## Advanced Features & Mechanics
Curious about how the mathematical adaptive learning model works under the hood, or how to write your own custom 15-minute cron configurations? 
👉 **[Read the Full Architecture & Customization Guide here](script-guide.md)**
