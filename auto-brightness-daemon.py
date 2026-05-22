#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface

CONFIG_FILE = os.path.expanduser("~/.config/auto-brightness/profiles.conf")
LOG_FILE = os.path.expanduser("~/.local/state/auto-brightness.log")
PAUSE_FILE = os.path.expanduser("~/.local/state/auto-brightness.paused")
STATE_MAX_AGE = 1200 # 20 minutes

def log_msg(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}\n"
    print(line, end="")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
        # Keep log file small (100 lines)
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        if len(lines) > 100:
            with open(LOG_FILE, "w") as f:
                f.writelines(lines[-100:])
    except Exception:
        pass

def parse_config():
    ambient = 0
    disabled = []
    points = {"default": {}} # dev -> {mins: pct}
    
    if not os.path.exists(CONFIG_FILE):
        return ambient, disabled, points
        
    with open(CONFIG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" not in line: continue
            k, v = line.split("=", 1)
            
            if k == "ambient_sensor":
                ambient = int(v) if v.isdigit() else 0
            elif k == "disabled_displays":
                disabled = [x for x in v.split(",") if x]
            else:
                try:
                    pct = int(v)
                    if "_" in k:
                        dev, hhmm = k.split("_", 1)
                    else:
                        dev = "default"
                        hhmm = k
                        
                    if len(hhmm) == 4 and hhmm.isdigit():
                        h, m = int(hhmm[:2]), int(hhmm[2:])
                        mins = h * 60 + m
                        if dev not in points: points[dev] = {}
                        points[dev][mins] = pct
                except Exception:
                    pass
    return ambient, disabled, points

def get_devices():
    devices = []
    try:
        out = subprocess.check_output(["kscreen-doctor", "-o"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            # simple parse
            if "Output:" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "Output:" and i+2 < len(parts):
                        devices.append(parts[i+2])
    except Exception:
        pass
        
    if not devices:
        import glob
        paths = glob.glob("/sys/class/backlight/*")
        devices = [os.path.basename(p) for p in paths if os.path.isdir(p)]
        
    if not devices:
        devices = ["default"]
    return devices

def get_brightness(dev):
    try:
        if dev != "default":
            out = subprocess.check_output(["brightnessctl", "-d", dev, "-m"], text=True, stderr=subprocess.DEVNULL)
        else:
            out = subprocess.check_output(["brightnessctl", "-m"], text=True, stderr=subprocess.DEVNULL)
        pct_str = out.strip().split(",")[3].replace("%", "")
        return int(pct_str)
    except Exception:
        return None

def set_brightness_smooth(dev, target_pct):
    current = get_brightness(dev)
    if current is None or current == target_pct:
        set_brightness_raw(dev, target_pct)
        return
        
    diff = target_pct - current
    steps = 10
    sleep_time = 0.05
    for i in range(1, steps + 1):
        step_val = current + int(diff * (i / steps))
        set_brightness_raw(dev, step_val)
        time.sleep(sleep_time)

def set_brightness_raw(dev, pct):
    try:
        if dev == "default":
            subprocess.run(["brightnessctl", "-q", "set", f"{pct}%"], stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["brightnessctl", "-d", dev, "-q", "set", f"{pct}%"], stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_lux():
    for path in ["/sys/bus/iio/devices/iio:device0/in_illuminance_input", "/sys/bus/iio/devices/iio:device0/in_illuminance_raw"]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    lux = int(f.read().strip())
                    return lux
            except Exception:
                pass
    return None

def calc_ambient_offset(lux):
    if lux is None: return 0
    if lux < 10: return -15
    elif lux < 50: return -10
    elif lux < 150: return -5
    elif lux > 3000: return 30
    elif lux > 1000: return 20
    elif lux > 500: return 10
    return 0

def run_adjustment():
    if os.path.exists(PAUSE_FILE):
        try:
            with open(PAUSE_FILE, "r") as f:
                paused_until = f.read().strip()
            if paused_until == "indefinite":
                return
            if int(time.time()) < int(paused_until):
                return
            os.remove(PAUSE_FILE)
        except Exception:
            pass

    ambient_on, disabled, points_map = parse_config()
    lux = get_lux() if ambient_on else None
    offset = calc_ambient_offset(lux)
    
    if ambient_on and lux is not None:
        log_msg(f"Ambient sensor active: lux={lux}, offset={offset}%")

    now = datetime.now()
    cur_mins = now.hour * 60 + now.minute
    
    for dev in get_devices():
        if dev in disabled:
            log_msg(f"Display auto-adjust disabled for {dev}")
            continue
            
        pts = points_map.get(dev, points_map.get("default", {}))
        if not pts:
            target = 15
            nearest_time = "0000"
        else:
            sorted_mins = sorted(pts.keys())
            if cur_mins < sorted_mins[0]:
                L_min = sorted_mins[-1] - 1440
                L_pct = pts[sorted_mins[-1]]
                U_min = sorted_mins[0]
                U_pct = pts[sorted_mins[0]]
            elif cur_mins > sorted_mins[-1]:
                L_min = sorted_mins[-1]
                L_pct = pts[sorted_mins[-1]]
                U_min = sorted_mins[0] + 1440
                U_pct = pts[sorted_mins[0]]
            else:
                for i in range(len(sorted_mins)-1):
                    if sorted_mins[i] <= cur_mins <= sorted_mins[i+1]:
                        L_min = sorted_mins[i]
                        L_pct = pts[sorted_mins[i]]
                        U_min = sorted_mins[i+1]
                        U_pct = pts[sorted_mins[i+1]]
                        break
            
            denom = U_min - L_min
            if denom == 0:
                target = L_pct
            else:
                target = L_pct + round((cur_mins - L_min) * (U_pct - L_pct) / denom)
                
            # Nearest for learning
            diff_L = abs(cur_mins - L_min)
            diff_U = abs(U_min - cur_mins)
            nearest = L_min if diff_L <= diff_U else U_min
            nearest = (nearest + 1440) % 1440
            nearest_time = f"{nearest//60:02d}{nearest%60:02d}"

        target += offset
        target = max(5, min(100, target))
        
        current = get_brightness(dev)
        if current is not None:
            state_file = os.path.expanduser(f"~/.local/state/auto-brightness.{dev}.state")
            now_epoch = int(time.time())
            
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        parts = f.read().split()
                        last_set = int(parts[0])
                        last_time = int(parts[1])
                    
                    age = now_epoch - last_time
                    diff = abs(current - last_set)
                    
                    if age <= STATE_MAX_AGE and diff > 5:
                        target = current
                        log_msg(f"Learned new manual preference for {dev}: {current}% for profile {nearest_time}")
                        subprocess.run(["notify-send", "-a", "LBrightness", "-i", "display-brightness-symbolic", "LBrightness: Learned Preference", f"Saved new brightness {current}% for {nearest_time[:2]}:{nearest_time[2:]}"], stderr=subprocess.DEVNULL)
                        
                        # Update config
                        with open(CONFIG_FILE, "r") as f:
                            lines = f.readlines()
                        prefix = f"{dev}_{nearest_time}=" if dev in points_map else f"{nearest_time}="
                        found = False
                        for i, line in enumerate(lines):
                            if line.startswith(prefix):
                                lines[i] = f"{prefix}{current}\n"
                                found = True
                                break
                        if not found:
                            lines.append(f"{prefix}{current}\n")
                        with open(CONFIG_FILE, "w") as f:
                            f.writelines(lines)
                            
                        set_brightness_smooth(dev, target)
                    else:
                        if target != current:
                            set_brightness_smooth(dev, target)
                except Exception:
                    set_brightness_smooth(dev, target)
            else:
                set_brightness_smooth(dev, target)
                
            log_msg(f"{dev}: {target}% (was: {current})")
            try:
                with open(state_file, "w") as f:
                    f.write(f"{target} {now_epoch}")
            except Exception:
                pass

def on_sleep(sleeping):
    if not sleeping:
        # Wait a moment for screen to turn on
        QTimer.singleShot(1500, run_adjustment)

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    
    manager = QDBusInterface("org.freedesktop.login1", "/org/freedesktop/login1", "org.freedesktop.login1.Manager", QDBusConnection.systemBus())
    if manager.isValid():
        manager.PrepareForSleep.connect(on_sleep)
        
    timer = QTimer()
    timer.timeout.connect(run_adjustment)
    timer.start(15 * 60 * 1000) # 15 minutes
    
    # Run once on start
    QTimer.singleShot(100, run_adjustment)
    
    sys.exit(app.exec())
