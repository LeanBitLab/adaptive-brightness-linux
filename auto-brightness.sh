#!/bin/bash
# Adaptive Auto-Brightness for Linux
# Adjusts laptop backlight based on time of day and Learns from manual user adjustments!

LOGFILE="$HOME/.local/state/auto-brightness.log"
STATE_FILE="$HOME/.local/state/auto-brightness.state"
CONFIG_FILE="$HOME/.config/auto-brightness/profiles.conf"
PAUSE_FILE="$HOME/.local/state/auto-brightness.paused"

LAPTOP_DISPLAY="eDP-1"
EXTERNAL_DISPLAY="HDMI-A-1"

# Ensure log and state directories exist
mkdir -p "$(dirname "$LOGFILE")"

# Default profile initialization if config doesn't exist
if [[ ! -f "$CONFIG_FILE" ]]; then
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat << 'EOF' > "$CONFIG_FILE"
# Night (00:00 - 05:00)
0000=15
0100=15
0200=15
0300=15
0400=15
0500=15
# Early Morning (05:00 - 08:00)
0530=18
0600=22
0630=26
0700=30
0730=35
0800=40
# Morning (08:00 - 12:00)
0830=45
0900=50
0930=55
1000=60
1030=65
1100=70
1130=75
1200=80
# Afternoon (12:00 - 17:00)
1230=80
1300=78
1330=76
1400=74
1430=72
1500=70
1530=68
1600=66
1630=64
1700=62
# Evening (17:00 - 22:00)
1730=60
1800=55
1830=50
1900=45
1930=40
2000=35
2030=30
2100=26
2130=23
2200=20
# Late Night (22:00 - 00:00)
2230=18
2300=16
2330=15
EOF
fi

# 1. Temporary Pause Check
if [[ -f "$PAUSE_FILE" ]]; then
    read -r PAUSED_UNTIL < "$PAUSE_FILE"
    NOW_EPOCH=$(date +%s)
    if [[ "$PAUSED_UNTIL" == "indefinite" ]] || (( NOW_EPOCH < PAUSED_UNTIL )); then
        exit 0
    else
        # Pause expired, clean up the file
        rm -f "$PAUSE_FILE"
    fi
fi

# Get current time as HHMM and force base-10 interpretation
TIME=$(date +%H%M)

# Convert HHMM to minutes from midnight
hhmm_to_mins() {
    local t="$1"
    local h=$(( 10#${t:0:2} ))
    local m=$(( 10#${t:2:2} ))
    echo $(( h * 60 + m ))
}

CUR_MINS=$(hhmm_to_mins "$TIME")

# Parse configuration file for global settings
ambient_sensor_enabled=0
disabled_displays=""

while IFS='=' read -r pt pv || [ -n "$pt" ]; do
    [[ -z "$pt" || "$pt" == "#"* ]] && continue
    if [[ "$pt" == "ambient_sensor" ]]; then
        ambient_sensor_enabled=$pv
        continue
    fi
    if [[ "$pt" == "disabled_displays" ]]; then
        disabled_displays=$pv
        continue
    fi
done < "$CONFIG_FILE"

# Function: get interpolated target brightness for a specific device
# Sets: DEV_TARGET_PERCENT, DEV_PROFILE_TIME
get_interpolated_target() {
    local target_dev="$1"
    
    local -a pts=()
    local -a pvs=()
    local has_dev_specific=0
    
    # Parse config: prefer device-specific entries, fall back to default
    while IFS='=' read -r pt pv || [ -n "$pt" ]; do
        [[ -z "$pt" || "$pt" == "#"* ]] && continue
        [[ "$pt" == "ambient_sensor" || "$pt" == "disabled_displays" ]] && continue
        
        # Check for device-specific entry: DEVNAME_HHMM=val
        if [[ "$pt" =~ ^${target_dev}_([0-9]{4})$ ]]; then
            local time_part="${BASH_REMATCH[1]}"
            local mins=$(hhmm_to_mins "$time_part")
            pts+=($mins)
            pvs+=($pv)
            has_dev_specific=1
        fi
    done < "$CONFIG_FILE"
    
    # If no device-specific entries found, use default (bare HHMM=val)
    if (( has_dev_specific == 0 )); then
        while IFS='=' read -r pt pv || [ -n "$pt" ]; do
            [[ -z "$pt" || "$pt" == "#"* ]] && continue
            [[ "$pt" == "ambient_sensor" || "$pt" == "disabled_displays" ]] && continue
            if [[ "$pt" =~ ^[0-9]{4}$ ]]; then
                local mins=$(hhmm_to_mins "$pt")
                pts+=($mins)
                pvs+=($pv)
            fi
        done < "$CONFIG_FILE"
    fi
    
    local num_pts=${#pts[@]}
    if (( num_pts == 0 )); then
        DEV_TARGET_PERCENT=15
        DEV_PROFILE_TIME="0000"
        return
    fi
    
    # Bubble sort
    local -a idxs=()
    for ((i=0; i<num_pts; i++)); do idxs+=($i); done
    for ((i=0; i<num_pts-1; i++)); do
        for ((j=0; j<num_pts-i-1; j++)); do
            local idx1=${idxs[j]}
            local idx2=${idxs[j+1]}
            if (( pts[idx1] > pts[idx2] )); then
                idxs[j]=$idx2
                idxs[j+1]=$idx1
            fi
        done
    done
    
    local -a sorted_pts=()
    local -a sorted_pvs=()
    for ((i=0; i<num_pts; i++)); do
        local idx=${idxs[i]}
        sorted_pts+=(${pts[idx]})
        sorted_pvs+=(${pvs[idx]})
    done
    
    # Find bounding points
    local L_min="" L_pct="" U_min="" U_pct=""
    
    if (( CUR_MINS < sorted_pts[0] )); then
        L_min=$(( sorted_pts[num_pts-1] - 1440 ))
        L_pct=${sorted_pvs[num_pts-1]}
        U_min=${sorted_pts[0]}
        U_pct=${sorted_pvs[0]}
    elif (( CUR_MINS > sorted_pts[num_pts-1] )); then
        L_min=${sorted_pts[num_pts-1]}
        L_pct=${sorted_pvs[num_pts-1]}
        U_min=$(( sorted_pts[0] + 1440 ))
        U_pct=${sorted_pvs[0]}
    else
        for ((i=0; i<num_pts-1; i++)); do
            if (( CUR_MINS >= sorted_pts[i] && CUR_MINS <= sorted_pts[i+1] )); then
                L_min=${sorted_pts[i]}
                L_pct=${sorted_pvs[i]}
                U_min=${sorted_pts[i+1]}
                U_pct=${sorted_pvs[i+1]}
                break
            fi
        done
    fi
    
    # Interpolate
    local denom=$(( U_min - L_min ))
    if (( denom == 0 )); then
        DEV_TARGET_PERCENT=$L_pct
    else
        local num=$(( (CUR_MINS - L_min) * (U_pct - L_pct) ))
        if (( (num >= 0 && denom >= 0) || (num < 0 && denom < 0) )); then
            DEV_TARGET_PERCENT=$(( L_pct + (num + denom/2) / denom ))
        else
            DEV_TARGET_PERCENT=$(( L_pct + (num - denom/2) / denom ))
        fi
    fi
    
    # Nearest profile point for learning
    local diff_L=$(( CUR_MINS - L_min ))
    diff_L=${diff_L#-}
    local diff_U=$(( U_min - CUR_MINS ))
    diff_U=${diff_U#-}
    
    local nearest_mins
    if (( diff_L <= diff_U )); then
        nearest_mins=$L_min
    else
        nearest_mins=$U_min
    fi
    nearest_mins=$(( (nearest_mins + 1440) % 1440 ))
    local nearest_h=$(( nearest_mins / 60 ))
    local nearest_m=$(( nearest_mins % 60 ))
    DEV_PROFILE_TIME=$(printf "%02d%02d" $nearest_h $nearest_m)
}

# 2. Ambient light sensor offset
ambient_offset=0
if [[ "$ambient_sensor_enabled" == "1" ]]; then
    LUX=""
    if [[ -f "/sys/bus/iio/devices/iio:device0/in_illuminance_input" ]]; then
        LUX=$(cat "/sys/bus/iio/devices/iio:device0/in_illuminance_input" 2>/dev/null)
    elif [[ -f "/sys/bus/iio/devices/iio:device0/in_illuminance_raw" ]]; then
        LUX=$(cat "/sys/bus/iio/devices/iio:device0/in_illuminance_raw" 2>/dev/null)
    fi

    if [[ -n "$LUX" && "$LUX" =~ ^[0-9]+$ ]]; then
        if (( LUX < 10 )); then
            ambient_offset=-15
        elif (( LUX < 50 )); then
            ambient_offset=-10
        elif (( LUX < 150 )); then
            ambient_offset=-5
        elif (( LUX > 3000 )); then
            ambient_offset=30
        elif (( LUX > 1000 )); then
            ambient_offset=20
        elif (( LUX > 500 )); then
            ambient_offset=10
        fi
        echo "[$(date '+%Y-%m-%d %H:%M')] Ambient sensor active: lux=${LUX}, offset=${ambient_offset}%" >> "$LOGFILE"
    fi
fi

# Helper to get brightness for a display (supports kscreen-doctor and brightnessctl fallback)
get_display_brightness() {
    local dev="$1"
    
    # 1. Try kscreen-doctor if available
    if command -v kscreen-doctor &>/dev/null; then
        local pct=""
        local current_dev=""
        while read -r line; do
            clean_line=$(echo "$line" | sed "s/\x1b\[[0-9;]*[a-zA-Z]//g")
            if [[ "$clean_line" =~ ^Output:[[:space:]]*[0-9]+[[:space:]]+([a-zA-Z0-9-]+) ]]; then
                current_dev="${BASH_REMATCH[1]}"
            elif [[ "$current_dev" == "$dev" && "$clean_line" == *"Brightness control:"* ]]; then
                if [[ "$clean_line" =~ set[[:space:]]+to[[:space:]]+([0-9]+)% ]]; then
                    pct="${BASH_REMATCH[1]}"
                    echo "$pct"
                    return 0
                fi
            fi
        done < <(kscreen-doctor -o 2>/dev/null)
    fi

    # 2. Try brightnessctl fallback
    if command -v brightnessctl &>/dev/null; then
        local bctl_out=""
        if [[ "$dev" == "default" ]]; then
            bctl_out=$(brightnessctl -m)
        else
            bctl_out=$(brightnessctl -d "$dev" -m 2>/dev/null || brightnessctl -m)
        fi
        IFS=',' read -r _ _ _ dpct _ <<< "$bctl_out"
        echo "${dpct%\%}"
        return 0
    fi
    echo ""
    return 1
}

# Helper to set brightness for primary display (supports kscreen-doctor, KDE D-Bus, and brightnessctl fallback)
set_brightness() {
    local dev="$1"
    local pct="$2"

    # Try kscreen-doctor first if available and dev is not default
    if [[ "$dev" != "default" ]] && command -v kscreen-doctor &>/dev/null; then
        if kscreen-doctor output."$dev".brightness."$pct" &>/dev/null; then
            return 0
        fi
    fi

    local dbus_cmd=""
    if command -v qdbus6 &>/dev/null; then
        dbus_cmd="qdbus6"
    elif command -v qdbus &>/dev/null; then
        dbus_cmd="qdbus"
    fi

    # Try setting via KDE PowerDevil D-Bus interface so the status/slider updates
    if [[ -n "$dbus_cmd" ]] && $dbus_cmd org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/BrightnessControl &>/dev/null; then
        local val=$(( pct * 100 ))
        if $dbus_cmd org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/BrightnessControl org.kde.Solid.PowerManagement.Actions.BrightnessControl.setBrightnessSilent "$val" &>/dev/null; then
            return 0
        fi
    fi

    # Fallback to direct hardware control via brightnessctl
    if command -v brightnessctl &>/dev/null; then
        if [[ "$dev" == "default" ]]; then
            brightnessctl -q set "${pct}%"
        else
            brightnessctl -d "$dev" -q set "${pct}%" 2>/dev/null || brightnessctl -q set "${pct}%"
        fi
    fi
}

# 3. Discover all available backlight devices
declare -a devices
if command -v kscreen-doctor &>/dev/null; then
    while read -r line; do
        clean_line=$(echo "$line" | sed "s/\x1b\[[0-9;]*[a-zA-Z]//g")
        if [[ "$clean_line" =~ ^Output:[[:space:]]*[0-9]+[[:space:]]+([a-zA-Z0-9-]+) ]]; then
            dev_name="${BASH_REMATCH[1]}"
            devices+=("$dev_name")
        fi
    done < <(kscreen-doctor -o 2>/dev/null)
fi

if (( ${#devices[@]} == 0 )); then
    for dev in /sys/class/backlight/*; do
        if [[ -d "$dev" ]]; then
            devices+=("$(basename "$dev")")
        fi
    done
fi

if (( ${#devices[@]} == 0 )); then
    devices=("default")
fi

# Adaptive Learning: Max age (seconds) for state file to be considered fresh (20 min)
STATE_MAX_AGE=1200
NOW_EPOCH=$(date +%s)

# 4. Process each device independently
for dev in "${devices[@]}"; do
    # Skip disabled displays
    if [[ -n "$disabled_displays" && ",$disabled_displays," == *",$dev,"* ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M')] Display auto-adjust disabled for $dev" >> "$LOGFILE"
        continue
    fi
    
    # Get interpolated target for this specific device
    get_interpolated_target "$dev"
    
    # Apply ambient offset
    DEV_TARGET_PERCENT=$(( DEV_TARGET_PERCENT + ambient_offset ))
    if (( DEV_TARGET_PERCENT < 5 )); then DEV_TARGET_PERCENT=5; fi
    if (( DEV_TARGET_PERCENT > 100 )); then DEV_TARGET_PERCENT=100; fi
    
    # Device-specific state file
    local_state_file="$HOME/.local/state/auto-brightness.${dev}.state"
    
    # Get current brightness for this device
    CURRENT_PERCENT=$(get_display_brightness "$dev")
    
    if [[ -n "$CURRENT_PERCENT" ]]; then
        if [[ -f "$local_state_file" ]]; then
            read -r LAST_SET_PERCENT LAST_EPOCH < "$local_state_file"
            STATE_AGE=$(( NOW_EPOCH - ${LAST_EPOCH:-0} ))
            
            DIFF=$(( CURRENT_PERCENT - LAST_SET_PERCENT ))
            DIFF=${DIFF#-}
            
            # Learn if state is fresh AND user adjusted beyond 5% margin
            if (( STATE_AGE <= STATE_MAX_AGE && DIFF > 5 )); then
                DEV_TARGET_PERCENT=$CURRENT_PERCENT
                
                # Update config file for this device's profile time
                # If device has specific entries, update those; otherwise update default
                has_dev_entries=0
                if grep -q "^${dev}_" "$CONFIG_FILE" 2>/dev/null; then
                    has_dev_entries=1
                fi
                
                if (( has_dev_entries == 1 )); then
                    sed -i "s/^${dev}_${DEV_PROFILE_TIME}=.*/${dev}_${DEV_PROFILE_TIME}=${CURRENT_PERCENT}/" "$CONFIG_FILE"
                else
                    sed -i "s/^${DEV_PROFILE_TIME}=.*/${DEV_PROFILE_TIME}=${CURRENT_PERCENT}/" "$CONFIG_FILE"
                fi
                
                echo "[$(date '+%Y-%m-%d %H:%M')] Learned new manual preference for $dev: ${CURRENT_PERCENT}% for profile ${DEV_PROFILE_TIME}" >> "$LOGFILE"
                
                set_brightness "$dev" "$DEV_TARGET_PERCENT"
            else
                # Apply profile target if different from current
                if (( DEV_TARGET_PERCENT != CURRENT_PERCENT )); then
                    set_brightness "$dev" "$DEV_TARGET_PERCENT"
                fi
            fi
        else
            # First run for this device
            set_brightness "$dev" "$DEV_TARGET_PERCENT"
        fi
        
        echo "[$(date '+%Y-%m-%d %H:%M')] $dev: ${DEV_TARGET_PERCENT}% (was: ${CURRENT_PERCENT:-unknown})" >> "$LOGFILE"
        
        # Save state for this device
        echo "$DEV_TARGET_PERCENT $NOW_EPOCH" > "$local_state_file"
    fi
done

# Keep log file small (last 100 lines)
if [ -f "$LOGFILE" ]; then
    tail -100 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
fi

