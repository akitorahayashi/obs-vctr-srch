#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

echo "Running as $(whoami) (UID: $(id -u))"

# --- Application startup ready ---
echo "Application startup preparations completed."

# --- Start Uvicorn server (or run another command) ---
# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    # Execute command as current user
    exec "$@"
else
    # Start the server
    WORKERS=${NUM_OF_UVICORN_WORKERS:-4}
    echo "Starting server on 0.0.0.0:8000 with ${WORKERS} worker(s)..."
    # Start server as current user
    exec uvicorn src.main:app \
        --host "0.0.0.0" \
        --port "8000" \
        --workers "${WORKERS}" \
        --loop uvloop \
        --limit-concurrency 40
fi
