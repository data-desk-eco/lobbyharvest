#!/bin/bash

# Utility script to take screenshots during browser automation development
# Usage: ./screenshot.sh [output_filename]

OUTPUT="${1:-screenshot.png}"
PORT="${PLAYWRIGHT_DEBUG_PORT:-9222}"

echo "Taking screenshot from Playwright debug session on port $PORT..."
echo "Output will be saved to: $OUTPUT"

python3 -c "
from playwright.sync_api import sync_playwright
import sys

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp(f'http://localhost:${PORT}')
        page = browser.contexts[0].pages[0]
        page.screenshot(path='$OUTPUT')
        print('Screenshot saved successfully!')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
"