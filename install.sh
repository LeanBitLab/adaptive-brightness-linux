#!/bin/bash
# Installer for Adaptive Auto-Brightness

echo "Installing Adaptive Auto-Brightness..."

# Create necessary directories
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/auto-brightness"
mkdir -p "$HOME/.local/state"

# Copy the daemon and GUI
cp auto-brightness-daemon.py "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/auto-brightness-daemon.py"
cp gui.py "$HOME/.local/bin/auto-brightness-gui"
chmod +x "$HOME/.local/bin/auto-brightness-gui"

# Copy systemd units
cp auto-brightness.service "$HOME/.config/systemd/user/"

# Clean up old timer if exists
systemctl --user stop auto-brightness.timer 2>/dev/null || true
systemctl --user disable auto-brightness.timer 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/auto-brightness.timer"
rm -f "$HOME/.local/bin/auto-brightness.sh"

# Install desktop entry for menu launchers
mkdir -p "$HOME/.local/share/applications"
sed "s|Exec=auto-brightness-gui|Exec=$HOME/.local/bin/auto-brightness-gui|g" auto-brightness-gui.desktop > "$HOME/.local/share/applications/auto-brightness-gui.desktop"
update-desktop-database "$HOME/.local/share/applications/" &>/dev/null || true

# Reload systemd and enable service
systemctl --user daemon-reload
systemctl --user enable --now auto-brightness.service

echo "Installation complete!"
echo "The python daemon runs continuously in the background, smoothly adjusting brightness and listening for sleep/wake events."
echo "You can launch the GUI control panel via application menu ('Adaptive Brightness') or command 'auto-brightness-gui'."
