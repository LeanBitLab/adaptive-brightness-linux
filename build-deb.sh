#!/bin/bash
# Debian Package Builder for LBrightness (lbright)
# Maintained by LeanBitLab

set -e

echo "=== Building LBrightness Debian Package ==="

# Check requirements
if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: 'dpkg-deb' is required to build Debian packages."
    exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
    echo "Error: 'cargo' is required to compile lbright."
    exit 1
fi

# Extract version from Cargo.toml
VERSION=$(grep '^version' Cargo.toml | head -n 1 | cut -d '"' -f 2)
if [ -z "$VERSION" ]; then
    VERSION="0.1.0"
fi

# Detect system architecture
ARCH=$(dpkg --print-architecture 2>/dev/null || echo "amd64")

echo "Package Version: $VERSION"
echo "Architecture:    $ARCH"

# Build Rust release binary
echo "Compiling release binary..."
cargo build --release

# Define directories
STAGE_DIR="dist/deb_build"
DEBIAN_DIR="$STAGE_DIR/DEBIAN"
BIN_DIR="$STAGE_DIR/usr/bin"
SYSTEMD_DIR="$STAGE_DIR/usr/lib/systemd/user"
DOC_DIR="$STAGE_DIR/usr/share/doc/lbright"

# Clean previous build artifacts
rm -rf dist/
mkdir -p "$DEBIAN_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$SYSTEMD_DIR"
mkdir -p "$DOC_DIR"

echo "Staging files..."
# Install compiled binary
install -Dm755 target/release/lbright "$BIN_DIR/lbright"

# Systemd User Service unit (adjusted for global /usr/bin execution)
sed 's|%h/.local/bin/lbright|/usr/bin/lbright|g' lbright.service > "$SYSTEMD_DIR/lbright.service"
chmod 644 "$SYSTEMD_DIR/lbright.service"

# Copyright / Documentation
if [ -f "LICENSE" ]; then
    cp LICENSE "$DOC_DIR/copyright"
fi
if [ -f "README.md" ]; then
    cp README.md "$DOC_DIR/"
fi

echo "Generating package metadata..."
# Create DEBIAN/control
cat << EOF > "$DEBIAN_DIR/control"
Package: lbright
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: LeanBitLab <leanbitlab@users.noreply.github.com>
Depends: libc6
Recommends: ddcutil, i2c-tools
Provides: adaptive-brightness-linux, lbrightness
Replaces: adaptive-brightness-linux
Description: Lightweight adaptive screen brightness system for Linux
 High-performance Rust daemon for intelligent screen brightness
 control using direct sysfs kernel I/O, DDC/CI external monitor support,
 ALS ambient light smoothing, and an interactive ANSI terminal UI.
EOF

# Create DEBIAN/postinst
cat << 'EOF' > "$DEBIAN_DIR/postinst"
#!/bin/bash
set -e

if [ "$1" = "configure" ]; then
    echo "Reloading systemd user daemon..."
    systemctl --global daemon-reload 2>/dev/null || true
    echo ""
    echo "LBrightness (lbright) installed successfully!"
    echo "To start the background service for your user:"
    echo "  systemctl --user enable --now lbright.service"
    echo ""
    echo "To open the interactive menu: lbright tui"
    echo "To check system status:       lbright status"
fi
EOF
chmod 755 "$DEBIAN_DIR/postinst"

# Create DEBIAN/prerm
cat << 'EOF' > "$DEBIAN_DIR/prerm"
#!/bin/bash
set -e

if [ "$1" = "remove" ] || [ "$1" = "deconfigure" ]; then
    systemctl --global disable lbright.service 2>/dev/null || true
fi
EOF
chmod 755 "$DEBIAN_DIR/prerm"

# Build the Debian package
PACKAGE_NAME="lbright_${VERSION}_${ARCH}.deb"
echo "Compiling Debian package: $PACKAGE_NAME..."
dpkg-deb --root-owner-group --build "$STAGE_DIR" "$PACKAGE_NAME"

echo ""
echo "=== Build Complete ==="
echo "Package generated: $PACKAGE_NAME"
echo "Install with:      sudo dpkg -i $PACKAGE_NAME"

