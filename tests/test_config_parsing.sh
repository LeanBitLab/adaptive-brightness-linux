#!/bin/bash

# tests/test_config_parsing.sh
# Test script for configuration file parsing in auto-brightness.sh

set -e

echo "Starting config parsing test..."

TEST_HOME=$(mktemp -d)
export HOME="$TEST_HOME"

trap 'rm -rf "$TEST_HOME"' EXIT

# Mock binaries
mkdir -p "$TEST_HOME/mock-bin"
export PATH="$TEST_HOME/mock-bin:$PATH"

# Mock date command
cat << 'INNER_EOF' > "$TEST_HOME/mock-bin/date"
#!/bin/bash
if [[ "$*" == *"+%H%M"* ]] && [ -n "$MOCK_TIME" ]; then
    echo "$MOCK_TIME"
elif [[ "$*" == *"+%s"* ]]; then
    echo "1672531200"
else
    echo "2023-01-01 12:00"
fi
INNER_EOF
chmod +x "$TEST_HOME/mock-bin/date"

# Mock brightnessctl
cat << 'INNER_EOF' > "$TEST_HOME/mock-bin/brightnessctl"
#!/bin/bash
if [[ "$*" == *"-m"* ]]; then
    echo "mock,mock,mock,50%,mock"
fi
INNER_EOF
chmod +x "$TEST_HOME/mock-bin/brightnessctl"

# Mock qdbus and qdbus6 to return failure so tests use the brightnessctl fallback
cat << 'INNER_EOF' > "$TEST_HOME/mock-bin/qdbus"
#!/bin/bash
exit 1
INNER_EOF
chmod +x "$TEST_HOME/mock-bin/qdbus"

cat << 'INNER_EOF' > "$TEST_HOME/mock-bin/qdbus6"
#!/bin/bash
exit 1
INNER_EOF
chmod +x "$TEST_HOME/mock-bin/qdbus6"

# Create config
mkdir -p "$HOME/.config/auto-brightness"
mkdir -p "$HOME/.local/state"
CONFIG_FILE="$HOME/.config/auto-brightness/profiles.conf"
STATE_FILE="$HOME/.local/state/auto-brightness.state"

cat << 'INNER_EOF' > "$CONFIG_FILE"
# Test Configuration

0600=20
0830=45
1200=80
1800=40

# Comment to ignore
2200=10

# Testing trailing line with no newline at EOF
2300=5
INNER_EOF

# Ensure no trailing newline on the last line to test the edge case
truncate -s -1 "$CONFIG_FILE"

FAILED=0

assert_target() {
    local time_val=$1
    local expected=$2

    export MOCK_TIME=$time_val
    # Clean up all per-device state files
    rm -f "$HOME/.local/state/auto-brightness".*.state
    rm -f "$STATE_FILE"

    bash ./auto-brightness.sh

    # Script now writes per-device state files; check for default device
    local found_state=""
    for sf in "$HOME/.local/state/auto-brightness".*.state; do
        if [ -f "$sf" ]; then
            found_state="$sf"
            break
        fi
    done

    if [ -n "$found_state" ]; then
        read -r actual _ < "$found_state"
        if [ "$actual" == "$expected" ]; then
            echo "✅ Time $time_val -> Target $actual (Expected: $expected)"
        else
            echo "❌ Time $time_val -> Target $actual (Expected: $expected)"
            FAILED=1
        fi
    else
        echo "❌ STATE_FILE missing for time $time_val!"
        FAILED=1
    fi
}

# Run assertions
# Before first configured time (interpolates between last and first)
assert_target "0500" "18"

# Exactly on a time boundary
assert_target "0600" "20"

# Between boundaries (interpolates between 08:30 and 12:00)
assert_target "1000" "60"

# Exactly at peak
assert_target "1200" "80"

# Afternoon (interpolates between 12:00 and 18:00)
assert_target "1500" "60"

# Evening (interpolates between 18:00 and 22:00)
assert_target "1930" "29"

# Boundary with leading zeros parsing
assert_target "0830" "45"

# Late night (interpolates between 22:00 and 23:00)
assert_target "2230" "7"

# Very late night (last entry, tests the no-newline case, interpolates to 06:00 wrap)
assert_target "2359" "7"

if [ $FAILED -eq 1 ]; then
    echo "❌ Some config parsing tests failed!"
    exit 1
else
    echo "🎉 SUCCESS: All config parsing tests passed!"
fi
