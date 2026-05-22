#!/bin/bash
# Installer for Adaptive Auto-Brightness

echo "Installing Adaptive Auto-Brightness..."

# Create necessary directories
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/auto-brightness"
mkdir -p "$HOME/.local/state"

# Copy the script and GUI
cp auto-brightness.sh "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/auto-brightness.sh"
cp gui.py "$HOME/.local/bin/auto-brightness-gui"
chmod +x "$HOME/.local/bin/auto-brightness-gui"

# Copy systemd units
cp auto-brightness.service "$HOME/.config/systemd/user/"
cp auto-brightness.timer "$HOME/.config/systemd/user/"

# Install desktop entry for menu launchers
mkdir -p "$HOME/.local/share/applications"
sed "s|Exec=auto-brightness-gui|Exec=$HOME/.local/bin/auto-brightness-gui|g" auto-brightness-gui.desktop > "$HOME/.local/share/applications/auto-brightness-gui.desktop"
update-desktop-database "$HOME/.local/share/applications/" &>/dev/null || true

# Reload systemd and enable timer
systemctl --user daemon-reload
systemctl --user enable --now auto-brightness.timer
systemctl --user start auto-brightness.service

echo "Installation complete!"
echo "The script will run every 15 minutes and automatically learn your manual brightness changes."
echo "You can launch the GUI control panel via application menu ('Adaptive Brightness') or command 'auto-brightness-gui'."
