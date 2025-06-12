#!/bin/bash

# Variables
YQ_URL="https://github.com/mikefarah/yq/releases/download/v4.45.4/yq_linux_amd64"
DEST_DIR="$HOME/.local/bin"
DEST_FILE="yq"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Download the file and rename it to 'yq'
curl -L "$YQ_URL" -o "$DEST_DIR/$DEST_FILE"

# Make it executable
chmod +x "$DEST_DIR/$DEST_FILE"

echo "yq installed to $DEST_DIR/$DEST_FILE"

# Check if DEST_DIR is in PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$DEST_DIR"; then
    echo "Warning: $DEST_DIR is not in your PATH."
    echo "Add the following line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"$DEST_DIR:\$PATH\""
fi
