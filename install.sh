#!/bin/bash
# Installer for LBrightness (Rust)
set -e

echo "=== Installing LBrightness (lbright) ==="

if ! command -v cargo >/dev/null 2>&1; then
    echo "Error: 'cargo' is required to compile lbright."
    exit 1
fi

echo "Building release binary with Cargo..."
cargo build --release

# Ensure target directories exist
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/lbrightness"
mkdir -p "$HOME/.local/state/lbrightness"

# Stop old python daemon if running
systemctl --user stop auto-brightness.service 2>/dev/null || true
systemctl --user disable auto-brightness.service 2>/dev/null || true

# Install binary
install -Dm755 target/release/lbright "$HOME/.local/bin/lbright"
install -Dm644 lbright.service "$HOME/.config/systemd/user/lbright.service"

# Reload systemd and enable lbright service
systemctl --user daemon-reload
systemctl --user enable --now lbright.service 2>/dev/null || true

echo ""
echo "Installation complete!"
echo "Binary installed to: $HOME/.local/bin/lbright"
echo ""
echo "To check system status:       lbright status"
echo "To open interactive menu:     lbright tui"
echo "To scan displays:             lbright scan"
echo "To migrate old configuration: lbright migrate --dry-run"
echo "                              lbright migrate"
