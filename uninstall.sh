#!/bin/bash
# Uninstaller for LBrightness (lbright)
set -e

echo "=== Uninstalling LBrightness ==="

# Stop and disable systemd user service
systemctl --user stop lbright.service 2>/dev/null || true
systemctl --user disable lbright.service 2>/dev/null || true

# Remove binary and service unit
rm -f "$HOME/.local/bin/lbright"
rm -f "$HOME/.config/systemd/user/lbright.service"

systemctl --user daemon-reload

if [[ "$1" == "-y" ]]; then
    rm -rf "$HOME/.config/lbrightness"
    rm -rf "$HOME/.local/state/lbrightness"
    echo "Removed configuration and state files."
else
    echo -n "Do you want to delete user configuration (~/.config/lbrightness)? (y/N): "
    read -r -t 10 REPLY || REPLY="n"
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.config/lbrightness"
        rm -rf "$HOME/.local/state/lbrightness"
        echo "Removed configuration and state files."
    else
        echo "Kept configuration at ~/.config/lbrightness."
    fi
fi

echo "Uninstallation complete!"
