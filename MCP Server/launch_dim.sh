#!/bin/bash
# Launch DIM (pnpm start) tethered to this terminal, and open the app when ready.

set -euo pipefail

# Go to the script's directory (where your DIM project lives)
cd "$(dirname "$0")"

# In the background, wait for port 8080 to be ready, then open the browser
(
  # Try for up to ~2 minutes
  for i in {1..120}; do
    if nc -z localhost 8080 2>/dev/null; then
      open "https://localhost:8080/"
      exit 0
    fi
    sleep 1
  done
) &

WATCHER_PID=$!

# Clean up the watcher when this script exits (e.g., Ctrl+C or window closed)
cleanup() { kill "$WATCHER_PID" 2>/dev/null || true; }
trap cleanup EXIT

# Run DIM in the foreground so it's tied to this terminal window
pnpm start