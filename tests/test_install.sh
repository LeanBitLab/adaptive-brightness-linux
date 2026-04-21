#!/bin/bash

# tests/test_install.sh
# Test script for install.sh

# Exit on any error during setup
set -e

echo "Starting install.sh test..."

# Setup temporary HOME
TEST_HOME=$(mktemp -d)
echo "Using temporary HOME: $TEST_HOME"
export HOME="$TEST_HOME"

# Cleanup on exit
trap 'rm -rf "$TEST_HOME"' EXIT

# Mock systemctl to avoid interacting with the system's init system
MOCK_SYSTEMCTL_LOG="$TEST_HOME/systemctl_calls.log"
mkdir -p "$TEST_HOME/mock-bin"
cat <<EOF > "$TEST_HOME/mock-bin/systemctl"
#!/bin/bash
echo "systemctl \$*" >> "$MOCK_SYSTEMCTL_LOG"
EOF
chmod +x "$TEST_HOME/mock-bin/systemctl"
export PATH="$TEST_HOME/mock-bin:$PATH"

# Run the installer
# We use 'bash ./install.sh' to ensure we're testing the local version
bash ./install.sh

# Assertions
echo "Running assertions..."

# Function to assert directory existence
assert_dir() {
    if [ -d "$1" ]; then
        echo "✅ Directory exists: $1"
    else
        echo "❌ Directory MISSING: $1"
        exit 1
    fi
}

# Function to assert file existence
assert_file() {
    if [ -f "$1" ]; then
        echo "✅ File exists: $1"
    else
        echo "❌ File MISSING: $1"
        exit 1
    fi
}

# Function to assert file is executable
assert_exec() {
    if [ -x "$1" ]; then
        echo "✅ File is executable: $1"
    else
        echo "❌ File NOT executable: $1"
        exit 1
    fi
}

# 1. Check directories
assert_dir "$HOME/.local/bin"
assert_dir "$HOME/.config/systemd/user"
assert_dir "$HOME/.config/auto-brightness"
assert_dir "$HOME/.local/state"

# 2. Check files
assert_file "$HOME/.local/bin/auto-brightness.sh"
assert_exec "$HOME/.local/bin/auto-brightness.sh"
assert_file "$HOME/.config/systemd/user/auto-brightness.service"
assert_file "$HOME/.config/systemd/user/auto-brightness.timer"

# 3. Check systemctl calls
if grep -q "systemctl --user daemon-reload" "$MOCK_SYSTEMCTL_LOG" && \
   grep -q "systemctl --user enable --now auto-brightness.timer" "$MOCK_SYSTEMCTL_LOG" && \
   grep -q "systemctl --user start auto-brightness.service" "$MOCK_SYSTEMCTL_LOG"; then
    echo "✅ systemctl called with correct arguments"
else
    echo "❌ systemctl calls INCORRECT"
    echo "Calls recorded:"
    cat "$MOCK_SYSTEMCTL_LOG"
    exit 1
fi

echo "🎉 SUCCESS: All install.sh tests passed!"
