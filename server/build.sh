#!/usr/bin/env bash
# Render build script

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Build complete!"
