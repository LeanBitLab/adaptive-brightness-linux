#!/bin/bash

# tests/test_auto_brightness.sh
# Test script for adaptive learning logic in auto-brightness.sh

# Exit on any error during setup
set -e

echo "Starting auto-brightness.sh adaptive learning test..."

# Setup temporary HOME
TEST_HOME=$(mktemp -d)
echo "Using temporary HOME: $TEST_HOME"
export HOME="$TEST_HOME"

# Cleanup on exit
trap 'rm -rf "$TEST_HOME"' EXIT

# Mock date binary to control the time (12:00)
mkdir -p "$TEST_HOME/mock-bin"
cat << 'EOF' > "$TEST_HOME/mock-bin/date"
#!/bin/bash
if [ "$1" = "+%H%M" ]; then
    echo "1200"
else
    /bin/date "$@"
fi
EOF
chmod +x "$TEST_HOME/mock-bin/date"

# Mock brightnessctl to simulate current brightness and capture sets
export MOCK_BRIGHTNESS_LOG="$TEST_HOME/brightness_calls.log"
cat << 'EOF' > "$TEST_HOME/mock-bin/brightnessctl"
#!/bin/bash
if [ "$1" = "-m" ]; then
    echo "intel_backlight,backlight,100,${MOCK_CURRENT_PERCENT}%,200"
else
    echo "brightnessctl $*" >> "$MOCK_BRIGHTNESS_LOG"
fi
EOF
chmod +x "$TEST_HOME/mock-bin/brightnessctl"

export PATH="$TEST_HOME/mock-bin:$PATH"

# Setup directories
mkdir -p "$HOME/.local/state"
mkdir -p "$HOME/.config/auto-brightness"

CONFIG_FILE="$HOME/.config/auto-brightness/profiles.conf"
STATE_FILE="$HOME/.local/state/auto-brightness.state"

# Test variables
export MOCK_CURRENT_PERCENT

# Helper to setup initial state for a test case
setup_case() {
    local target_profile_pct="$1"
    local state_pct="$2"
    local current_pct="$3"

    cat << CONF > "$CONFIG_FILE"
1100=70
1200=${target_profile_pct}
1300=78
CONF

    echo "${state_pct}" > "$STATE_FILE"
    export MOCK_CURRENT_PERCENT="${current_pct}"
    rm -f "$MOCK_BRIGHTNESS_LOG"
}

# --- Case 1: Difference <= 5% ---
echo "Running Case 1: Difference <= 5% (No config update expected)"
# Target in profile is 80, state was 80, current is 84 (diff 4)
setup_case 80 80 84

bash ./auto-brightness.sh

# Assertions for Case 1
if grep -q "1200=80" "$CONFIG_FILE"; then
    echo "✅ Configuration file was NOT updated (Correct behavior)"
else
    echo "❌ Configuration file WAS updated (Incorrect behavior)"
    cat "$CONFIG_FILE"
    exit 1
fi

if grep -q "brightnessctl -q set 80%" "$MOCK_BRIGHTNESS_LOG"; then
    echo "✅ Applied original profile brightness (Correct behavior)"
else
    echo "❌ Did NOT apply original profile brightness (Incorrect behavior)"
    cat "$MOCK_BRIGHTNESS_LOG"
    exit 1
fi

if [ "$(cat "$STATE_FILE")" = "80" ]; then
    echo "✅ State file updated with original profile brightness (Correct behavior)"
else
    echo "❌ State file INCORRECT"
    cat "$STATE_FILE"
    exit 1
fi

# --- Case 2: Difference > 5% ---
echo "Running Case 2: Difference > 5% (Config update expected)"
# Target in profile is 80, state was 80, current is 70 (diff 10)
setup_case 80 80 70

bash ./auto-brightness.sh

# Assertions for Case 2
if grep -q "1200=70" "$CONFIG_FILE"; then
    echo "✅ Configuration file WAS updated permanently (Correct behavior)"
else
    echo "❌ Configuration file was NOT updated (Incorrect behavior)"
    cat "$CONFIG_FILE"
    exit 1
fi

if grep -q "brightnessctl -q set 70%" "$MOCK_BRIGHTNESS_LOG"; then
    echo "✅ Applied user's manual preference (Correct behavior)"
else
    echo "❌ Did NOT apply user's manual preference (Incorrect behavior)"
    cat "$MOCK_BRIGHTNESS_LOG"
    exit 1
fi

if [ "$(cat "$STATE_FILE")" = "70" ]; then
    echo "✅ State file updated with user's manual preference (Correct behavior)"
else
    echo "❌ State file INCORRECT"
    cat "$STATE_FILE"
    exit 1
fi

echo "🎉 SUCCESS: All auto-brightness logic tests passed!"
