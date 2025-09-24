#!/bin/bash
# Run commands with virtual display for headless browser automation

# Check if Xvfb is installed
if ! command -v Xvfb &> /dev/null; then
    echo "Xvfb not found. Installing..."
    sudo apt-get update && sudo apt-get install -y xvfb
fi

# Start Xvfb on display :99
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!

# Give Xvfb time to start
sleep 2

# Run the command passed as arguments
"$@"
EXIT_CODE=$?

# Clean up Xvfb
kill $XVFB_PID 2>/dev/null

exit $EXIT_CODE