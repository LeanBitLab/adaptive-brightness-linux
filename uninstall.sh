#!/bin/bash
# Uninstaller for Adaptive Auto-Brightness

echo "Uninstalling Adaptive Auto-Brightness..."

# Stop and disable systemd user service
systemctl --user stop auto-brightness.service 2>/dev/null || true
systemctl --user disable auto-brightness.service 2>/dev/null || true

# Remove daemon and GUI scripts
rm -f "$HOME/.local/bin/auto-brightness-daemon.py"
rm -f "$HOME/.local/bin/auto-brightness-gui"

# Remove systemd units
rm -f "$HOME/.config/systemd/user/auto-brightness.service"

# Remove desktop entries
rm -f "$HOME/.local/share/applications/auto-brightness-gui.desktop"
rm -f "$HOME/.config/autostart/auto-brightness-gui.desktop"

# Reload systemd and desktop database
systemctl --user daemon-reload
update-desktop-database "$HOME/.local/share/applications/" &>/dev/null || true

# Handle interactive or scripted removal of config and logs
if [[ "$1" == "-y" ]]; then
    rm -rf "$HOME/.config/auto-brightness"
    rm -f "$HOME/.local/state/auto-brightness.log"
    echo "Removed configuration and logs."
else
    echo -n "Do you want to delete user configuration and log files? (y/N): "
    read -r -t 10 REPLY || REPLY="n"
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.config/auto-brightness"
        rm -f "$HOME/.local/state/auto-brightness.log"
        echo "Removed configuration and logs."
    else
        echo "Kept configuration at ~/.config/auto-brightness and logs at ~/.local/state/auto-brightness.log."
    fi
fi

echo "Uninstallation complete!"
