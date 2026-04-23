#!/usr/bin/env bats

setup() {
    export TEST_TEMP_DIR="$(mktemp -d)"
    export HOME="$TEST_TEMP_DIR"
    export PATH="$TEST_TEMP_DIR/bin:$PATH"

    mkdir -p "$TEST_TEMP_DIR/bin"

    # Mock 'date' command
    cat << 'MOCK_EOF' > "$TEST_TEMP_DIR/bin/date"
#!/bin/bash
if [[ "$1" == "+%H%M" ]]; then
    echo "${MOCK_DATE_TIME:-1200}"
elif [[ "$1" == "+%Y-%m-%d %H:%M" ]]; then
    echo "2023-01-01 12:00"
else
    command date "$@"
fi
MOCK_EOF
    chmod +x "$TEST_TEMP_DIR/bin/date"

    # Mock 'brightnessctl' command
    cat << 'MOCK_EOF' > "$TEST_TEMP_DIR/bin/brightnessctl"
#!/bin/bash
if [[ "$1" == "-m" ]]; then
    # Return mock current brightness
    echo "backlight,backlight,100,${MOCK_CURRENT_BRIGHTNESS:-80}%,50"
elif [[ "$1" == "-q" && "$2" == "set" ]]; then
    echo "$3" > "$TEST_TEMP_DIR/brightness_set.log"
fi
MOCK_EOF
    chmod +x "$TEST_TEMP_DIR/bin/brightnessctl"
}

teardown() {
    rm -rf "$TEST_TEMP_DIR"
}

@test "Creates default config file if it doesn't exist" {
    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]
    [ -f "$HOME/.config/auto-brightness/profiles.conf" ]

    # Check some default values
    run grep "^1200=80" "$HOME/.config/auto-brightness/profiles.conf"
    [ "$status" -eq 0 ]
}

@test "Applies correct brightness based on time" {
    export MOCK_DATE_TIME="1200" # Afternoon, should be 80%
    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]

    # It should have set brightness to 80%
    [ -f "$TEST_TEMP_DIR/brightness_set.log" ]
    run cat "$TEST_TEMP_DIR/brightness_set.log"
    [ "$output" = "80%" ]
}

@test "Learns from manual brightness adjustment" {
    export MOCK_DATE_TIME="1200"

    # Force default config creation first
    bash ./auto-brightness.sh

    # Initial state
    mkdir -p "$HOME/.local/state"
    echo "80" > "$HOME/.local/state/auto-brightness.state"

    # Mock user changed brightness to 90%
    export MOCK_CURRENT_BRIGHTNESS="90"

    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]

    # It should have set brightness to 90%
    [ -f "$TEST_TEMP_DIR/brightness_set.log" ]
    run cat "$TEST_TEMP_DIR/brightness_set.log"
    [ "$output" = "90%" ]

    # Config file should be updated
    run grep "^1200=90" "$HOME/.config/auto-brightness/profiles.conf"
    [ "$status" -eq 0 ]

    # State file should be updated
    run cat "$HOME/.local/state/auto-brightness.state"
    [ "$output" = "90" ]
}

@test "Does not learn if adjustment is 5% or less" {
    export MOCK_DATE_TIME="1200"

    # Force default config creation first
    bash ./auto-brightness.sh

    # Initial state
    mkdir -p "$HOME/.local/state"
    echo "80" > "$HOME/.local/state/auto-brightness.state"

    # Mock user changed brightness to 83% (within 5% margin)
    export MOCK_CURRENT_BRIGHTNESS="83"

    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]

    # It should NOT update config (should remain 80)
    run grep "^1200=80" "$HOME/.config/auto-brightness/profiles.conf"
    [ "$status" -eq 0 ]
}

@test "First run logic applies profile brightness without learning" {
    export MOCK_DATE_TIME="1200"
    export MOCK_CURRENT_BRIGHTNESS="90"

    # We don't create state file to simulate first run
    mkdir -p "$HOME/.local/state"

    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]

    # Target should be the profile value (80 for 1200), not the current mock brightness
    [ -f "$TEST_TEMP_DIR/brightness_set.log" ]
    run cat "$TEST_TEMP_DIR/brightness_set.log"
    [ "$output" = "80%" ]

    # State file should now be created with the applied profile brightness
    [ -f "$HOME/.local/state/auto-brightness.state" ]
    run cat "$HOME/.local/state/auto-brightness.state"
    [ "$output" = "80" ]
}

@test "Log file truncation keeps last 100 lines" {
    mkdir -p "$HOME/.local/state"
    # Create a dummy log file with 105 lines
    for i in {1..105}; do
        echo "Log line $i" >> "$HOME/.local/state/auto-brightness.log"
    done

    run bash ./auto-brightness.sh
    [ "$status" -eq 0 ]

    # The script adds one more line during execution, so before truncation it was 106.
    # After truncation it should be exactly 100 lines.
    run wc -l < "$HOME/.local/state/auto-brightness.log"
    # wc -l output might have leading spaces depending on implementation, so use trim
    # Or just compare integer directly:
    [ $(echo "$output" | tr -d ' ') -eq 100 ]
}
