#!/bin/bash
set -e

MARKER_FILE="/browsers/.installed"

# First run: install browsers
if [ ! -f "$MARKER_FILE" ]; then
    echo "=== First run: Installing browser engines ==="

    # Create browsers directory if it doesn't exist
    mkdir -p /browsers

    echo "Installing Camoufox..."
    python -m camoufox fetch || echo "Camoufox install failed, continuing..."

    echo "Installing Patchright Chromium..."
    patchright install chromium || echo "Patchright install failed, continuing..."

    # Create marker
    touch "$MARKER_FILE"
    echo "=== Browser installation complete ==="
fi

# Run the command
exec "$@"
