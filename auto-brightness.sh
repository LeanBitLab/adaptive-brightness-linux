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
0000=15
0500=15
0530=20
0600=26
0630=32
0700=38
0730=43
0800=49
0830=54
0900=60
1700=56
1730=53
1800=49
1830=45
1900=41
1930=38
2000=34
2030=30
2100=26
2130=23
2200=19
2230=15
2300=15
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
if command -v brightnessctl &> /dev/null; then
    # Calculate current brightness percentage
    CURRENT_PERCENT=$(brightnessctl -m | cut -d, -f4 | tr -d '%')
    
    if [[ -f "$STATE_FILE" ]]; then
        LAST_SET_PERCENT=$(cat "$STATE_FILE")
        # Find absolute difference (abs)
        DIFF=$(( CURRENT_PERCENT - LAST_SET_PERCENT ))
        DIFF=${DIFF#-}
        
        # If user manually adjusted brightness beyond a 2% rounding margin
        if (( DIFF > 2 )); then
            # We assume user knows best. Set target to what user manually chose.
            TARGET_PERCENT=$CURRENT_PERCENT
            
            # Update the configuration file permanently for the current active profile block!
            sed -i "s/^${CURRENT_PROFILE_TIME}=.*/${CURRENT_PROFILE_TIME}=${CURRENT_PERCENT}/" "$CONFIG_FILE"
            echo "[$(date '+%Y-%m-%d %H:%M')] Learned new manual preference: ${CURRENT_PERCENT}% for profile ${CURRENT_PROFILE_TIME}" >> "$LOGFILE"
        fi
    fi

    # Apply the brightness
    brightnessctl -q set "${TARGET_PERCENT}%"
    echo "[$(date '+%Y-%m-%d %H:%M')] Laptop: ${TARGET_PERCENT}%" >> "$LOGFILE"
    
    # Save what we explicitly set to compare against next time
    echo "$TARGET_PERCENT" > "$STATE_FILE"
fi

# Keep log file small (last 100 lines)
if [ -f "$LOGFILE" ]; then
    tail -100 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
fi
