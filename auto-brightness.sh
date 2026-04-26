#!/bin/bash
# Adaptive Auto-Brightness for Linux
# Adjusts laptop backlight based on time of day and Learns from manual user adjustments!

LOGFILE="$HOME/.local/state/auto-brightness.log"
STATE_FILE="$HOME/.local/state/auto-brightness.state"
CONFIG_FILE="$HOME/.config/auto-brightness/profiles.conf"

LAPTOP_DISPLAY="eDP-1"
EXTERNAL_DISPLAY="HDMI-A-1"

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

# Get current time as HHMM and force base-10 interpretation
TIME=$(date +%H%M)
TIME_VAL=$(( 10#$TIME ))

# Force external display to 100% (User preference for low-brightness monitor)
EXTERNAL_PERCENT=100

# Parse the configuration file to determine the active block
TARGET_PERCENT=15 # Safe fallback
CURRENT_PROFILE_TIME="0000"

while IFS='=' read -r pt pv || [ -n "$pt" ]; do
    # Skip empty lines or comments
    [[ -z "$pt" || "$pt" == "#"* ]] && continue
    if (( TIME_VAL >= 10#${pt} )); then
        TARGET_PERCENT=$pv
        CURRENT_PROFILE_TIME=$pt
    fi
done < "$CONFIG_FILE"

# Adaptive Learning: Check for recent manual adjustments
# Max age (seconds) for state file to be considered fresh (20 min)
STATE_MAX_AGE=1200

if command -v brightnessctl &> /dev/null; then
    # Get current brightness percentage (round to integer)
    CURRENT_PERCENT=$(brightnessctl -m | awk -F, '{sub("%", "", $4); printf "%.0f\n", $4}')
    NOW_EPOCH=$(date +%s)

    if [[ -f "$STATE_FILE" ]]; then
        read -r LAST_SET_PERCENT LAST_EPOCH < "$STATE_FILE"
        # Determine if state file is fresh enough for learning
        STATE_AGE=$(( NOW_EPOCH - ${LAST_EPOCH:-0} ))

        # Find absolute difference (abs)
        DIFF=$(( CURRENT_PERCENT - LAST_SET_PERCENT ))
        DIFF=${DIFF#-}

        # Only learn if state is fresh (script ran recently) AND user adjusted beyond 5% margin
        if (( STATE_AGE <= STATE_MAX_AGE && DIFF > 5 )); then
            # We assume user knows best. Set target to what user manually chose.
            TARGET_PERCENT=$CURRENT_PERCENT

            # Update the configuration file permanently for the current active profile block!
            sed -i "s/^${CURRENT_PROFILE_TIME}=.*/${CURRENT_PROFILE_TIME}=${CURRENT_PERCENT}/" "$CONFIG_FILE"
            echo "[$(date '+%Y-%m-%d %H:%M')] Learned new manual preference: ${CURRENT_PERCENT}% for profile ${CURRENT_PROFILE_TIME}" >> "$LOGFILE"
            
            # Apply the user's preferred brightness
            brightnessctl -q set "${TARGET_PERCENT}%"
        else
            # Apply the profile brightness only if it differs from current
            if (( TARGET_PERCENT != CURRENT_PERCENT )); then
                brightnessctl -q set "${TARGET_PERCENT}%"
            fi
        fi
    else
        # First run - just apply the profile brightness
        brightnessctl -q set "${TARGET_PERCENT}%"
    fi

    echo "[$(date '+%Y-%m-%d %H:%M')] Laptop: ${TARGET_PERCENT}% (was: ${CURRENT_PERCENT:-unknown})" >> "$LOGFILE"

    # Save what we explicitly set, along with current epoch for staleness check
    echo "$TARGET_PERCENT $NOW_EPOCH" > "$STATE_FILE"
fi

# Keep log file small (last 100 lines)
if [ -f "$LOGFILE" ]; then
    tail -100 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
fi
