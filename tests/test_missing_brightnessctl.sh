#!/bin/bash

# tests/test_missing_brightnessctl.sh
# Test that auto-brightness.sh gracefully handles a missing brightnessctl command

# Exit on any error during setup
set -e

echo "Starting missing brightnessctl test..."

# Setup temporary HOME
TEST_HOME=$(mktemp -d)
echo "Using temporary HOME: $TEST_HOME"
export HOME="$TEST_HOME"

# Cleanup on exit
trap 'rm -rf "$TEST_HOME"' EXIT

# Mock 'command' builtin to simulate missing brightnessctl
command() {
    if [[ "$1" == "-v" && "$2" == "brightnessctl" ]]; then
        return 1
    fi
    builtin command "$@"
}
export -f command

# Run the script
echo "Running auto-brightness.sh..."
# Run directly with bash (exported functions are inherited by child bash)
bash ./auto-brightness.sh

# Assertions
echo "Running assertions..."

# 1. Config file should be created
CONFIG_FILE="$HOME/.config/auto-brightness/profiles.conf"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Config file created: $CONFIG_FILE"
else
    echo "❌ Config file MISSING: $CONFIG_FILE"
    exit 1
fi

# 2. State file should NOT be created since brightnessctl is missing
STATE_FILE="$HOME/.local/state/auto-brightness.state"
if [ ! -f "$STATE_FILE" ]; then
    echo "✅ State file NOT created (as expected): $STATE_FILE"
else
    echo "❌ State file SHOULD NOT EXIST: $STATE_FILE"
    exit 1
fi

echo "🎉 SUCCESS: Missing brightnessctl test passed!"
