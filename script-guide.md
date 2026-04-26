# Comprehensive Guide to Adaptive Brightness

Welcome to the `adaptive-brightness-linux` Guide by **LeanBitLab**! This document deeply explains the architecture, learning mechanism, and customization options for the script.

## Core Files & Architecture
The system consists of three main components:
1. **The Core Script (`auto-brightness.sh`)**: The bash logic that calculates time, parses profiles, evaluates manual user input, and communicates with your display panel.
2. **The Configuration File (`profiles.conf`)**: A static state file stored in `~/.config/auto-brightness/profiles.conf` that contains Key-Value pairs matching time to brightness percentages.
3. **Systemd Services (`.timer` & `.service`)**: Standard Linux daemons that wake up the script exactly every 15 minutes without maintaining a heavy background daemon/process.

---

## 🚀 The Adaptive Learning Mechanism

The primary innovation in this script is its ability to "learn" from you natively. Here is the step-by-step logic map of how it detects a manual change:

### 1. State Retention
Whenever the script natively applies a brightness value (e.g., `45%`), it saves that value along with the current **Unix Epoch Timestamp** into a microscopic cache file at `~/.local/state/auto-brightness.state`. This allows the script to know exactly *when* the last update occurred.

### 2. Difference & Staleness Calculation
15 minutes later, the `systemd` timer executes the script again.
Before the script blindly applies the *next* scheduled brightness, it performs two checks:
1.  **Staleness Check**: It compares the current time with the timestamp in the *State Cache*. If more than **20 minutes** have passed (e.g., the laptop was powered off or suspended), the script ignores any manual adjustments to prevent "false learning" from stale data.
2.  **Difference Check**: If the cache is fresh, it compares the *Actual Brightness* (from `brightnessctl -m`) with the *State Cache*.

*   If `Actual == Cache`, no intervention detected.
*   If `Actual != Cache` (with a >5% margin) **AND the cache is fresh**, the script mathematically concludes the User changed the brightness manually and triggers learning.

### 3. Profile Injection
When it detects user intervention, it intercepts the regular schedule! It pulls your newly modified screen percentage and dynamically rewrites the configuration for the active time block in `profiles.conf`.

For example, if the script applied `15%` at 00:00, but you manually ramped it up to `73%` at 00:05, the next interval check will detect the 58% deviation. It will immediately `sed` replace `0000=15` with `0000=73` inside the config file. From that day onward, your laptop will naturally apply `73%` between midnight and 5:00 AM!

### 4. Enhanced Logging
The log file now shows both the target brightness and the previous value:
```text
[2026-03-29 00:17] Laptop: 52% (was: 52)
[2026-03-29 09:00] Laptop: 50% (was: 45)
```
This helps you verify the script is making changes and track learning events.

---

## 🛠 Advanced Customization

### Modifying the Active Hours
By default, the script ships with 15-30 minute intervals covering the full 24-hour day with smooth transitions:
- **Night (00:00-05:00):** Constant low brightness (15%)
- **Early Morning (05:00-08:00):** Gradual wake-up ramp (15% → 40%)
- **Morning (08:00-12:00):** Steady increase to peak (45% → 80%)
- **Afternoon (12:00-17:00):** Slow decrease (80% → 62%)
- **Evening (17:00-22:00):** Wind-down phase (60% → 20%)
- **Late Night (22:00-00:00):** Prepare for sleep (18% → 15%)

To customize for your schedule:
1. Open `~/.config/auto-brightness/profiles.conf`
2. Add your custom timestamps in a 24-hour integer format (e.g. `0815`, `1400`).
```text
# Example of highly granular profiles
0800=40
0815=42
0830=45
0845=48
```
The script's bash array evaluator natively loops continuously until it matches `>=` the current time. It dynamically handles completely custom time gaps.

### Purging Learned State
If you've played with your brightness buttons too much and completely messed up your learned profile state, you can reset the learning memory by securely deleting the config.
```bash
rm ~/.config/auto-brightness/profiles.conf
```
The next time the script executes, it will safely detect the missing config and recreate the default, factory-calibrated curves!

## Privacy Guarantee
**LeanBitLab** strictly isolated all absolute system paths in this script. It uses dynamic environment variables (`$HOME`) and generic systemd targets (`%h`) ensuring it is entirely portable across Debian, Arch, Ubuntu, and Fedora ecosystems securely.
