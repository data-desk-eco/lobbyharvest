#!/bin/bash
# Screenshot utility for debugging Playwright scrapers
# Usage: ./screenshot.sh [browser_pid]

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <browser_pid>"
    echo "Captures a screenshot of a running Playwright browser"
    exit 1
fi

PID=$1
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="./screenshots"
mkdir -p "$OUTPUT_DIR"

# Use xwd to capture X window
if command -v xwd &> /dev/null; then
    xwd -id $(xdotool search --pid "$PID" | head -1) > "$OUTPUT_DIR/capture_$TIMESTAMP.xwd"
    echo "Screenshot saved to $OUTPUT_DIR/capture_$TIMESTAMP.xwd"
    echo "Convert with: convert $OUTPUT_DIR/capture_$TIMESTAMP.xwd $OUTPUT_DIR/capture_$TIMESTAMP.png"
else
    echo "xwd not found. Install x11-apps package."
    exit 1
fi