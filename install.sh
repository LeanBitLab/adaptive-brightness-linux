#!/bin/bash
# Installer for Adaptive Auto-Brightness

echo "Installing Adaptive Auto-Brightness..."

# Create necessary directories
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/auto-brightness"
mkdir -p "$HOME/.local/state"

# Copy the script
cp auto-brightness.sh "$HOME/.local/bin/"
chmod +x "$HOME/.local/bin/auto-brightness.sh"

# Copy systemd units
cp auto-brightness.service "$HOME/.config/systemd/user/"
cp auto-brightness.timer "$HOME/.config/systemd/user/"

# Reload systemd and enable timer
systemctl --user daemon-reload
systemctl --user enable --now auto-brightness.timer
systemctl --user start auto-brightness.service

echo "Installation complete!"
echo "The script will run every 15 minutes and automatically learn your manual brightness changes."
