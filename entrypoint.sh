#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# Switch to appuser if running as root, then re-exec
switch_to_user_if_root() {
    if [ "$(id -u)" = "0" ]; then
        echo "Running as root, switching to appuser..."
        mkdir -p "${OBSIDIAN_LOCAL_PATH}" "${VECTOR_DB_PATH}"
        chown -R appuser:appgroup "${OBSIDIAN_LOCAL_PATH}" "${VECTOR_DB_PATH}" 2>/dev/null || true
        exec gosu appuser "$0" "$@"
    fi
}

# Temporarily skip user switching to test Git operations
# switch_to_user_if_root "$@"
echo "Running as $(whoami) (UID: $(id -u))"

# Create necessary directories
if [ -n "${OBSIDIAN_LOCAL_PATH:-}" ]; then
    echo "Creating Obsidian directory: ${OBSIDIAN_LOCAL_PATH}"
    mkdir -p "${OBSIDIAN_LOCAL_PATH}"
    chmod 777 "${OBSIDIAN_LOCAL_PATH}"
fi

if [ -n "${VECTOR_DB_PATH:-}" ]; then
    echo "Creating vector database directory: ${VECTOR_DB_PATH}"
    mkdir -p "${VECTOR_DB_PATH}"
fi

# --- Application startup ready ---
echo "Application startup preparations completed."
echo "Note: Use /api/obs/setup endpoint to clone repository and perform initial sync."

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
