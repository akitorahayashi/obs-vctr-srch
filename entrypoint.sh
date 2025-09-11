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

# --- Clone/Update Obsidian Repository ---
clone_obsidian_repo() {
    echo "Setting up Obsidian repository..."
    
    # Check if repository is already cloned
    if [ -d "${OBSIDIAN_LOCAL_PATH}/.git" ]; then
        echo "Repository already exists. Updating..."
        cd "${OBSIDIAN_LOCAL_PATH}"
        git fetch origin "${OBSIDIAN_BRANCH}" && git reset --hard "origin/${OBSIDIAN_BRANCH}"
        cd -
        return 0
    fi
    
    # Clear directory contents if exists (for Docker volume case)
    if [ -d "${OBSIDIAN_LOCAL_PATH}" ] && [ "$(ls -A "${OBSIDIAN_LOCAL_PATH}" 2>/dev/null)" ]; then
        echo "Clearing existing directory contents: ${OBSIDIAN_LOCAL_PATH}"
        find "${OBSIDIAN_LOCAL_PATH}" -mindepth 1 -delete 2>/dev/null || true
    fi
    
    # Create directory with full permissions
    mkdir -p "${OBSIDIAN_LOCAL_PATH}"
    chmod 777 "${OBSIDIAN_LOCAL_PATH}"
    
    # Build git URL with token for private repos
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        # Extract repo info from URL
        REPO_PART=$(echo "${OBSIDIAN_REPO_URL}" | sed 's|https://github.com/||')
        CLONE_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PART}"
        echo "Cloning private repository with token..."
    else
        CLONE_URL="${OBSIDIAN_REPO_URL}"
        echo "Cloning public repository..."
    fi
    
    # Clone repository with proper permissions
    git config --global --add safe.directory '*'
    if git clone -b "${OBSIDIAN_BRANCH}" "${CLONE_URL}" "${OBSIDIAN_LOCAL_PATH}"; then
        echo "Successfully cloned Obsidian repository to ${OBSIDIAN_LOCAL_PATH}"
        
        # Remove .git directory to avoid conflicts
        if [ -d "${OBSIDIAN_LOCAL_PATH}/.git" ]; then
            rm -rf "${OBSIDIAN_LOCAL_PATH}/.git"
            echo "Removed .git directory for security"
        fi
    else
        echo "Failed to clone repository. Please check your OBSIDIAN_REPO_URL and GITHUB_TOKEN settings."
        echo "For private repositories, make sure GITHUB_TOKEN is set with repo access."
        exit 1
    fi
}

# Temporarily skip user switching to test Git operations
# switch_to_user_if_root "$@"
echo "Running as $(whoami) (UID: $(id -u))"

# Clone Obsidian repo if settings are provided
if [ -n "${OBSIDIAN_REPO_URL:-}" ] && [ -n "${OBSIDIAN_LOCAL_PATH:-}" ]; then
    clone_obsidian_repo
else
    echo "Obsidian settings not provided, skipping repository clone..."
fi

# --- Perform initial sync if needed ---
perform_initial_sync() {
    echo "Checking if initial sync is needed..."
    
    # Check if chroma_db directory exists and has data
    if [ ! -d "${VECTOR_DB_PATH}" ] || [ -z "$(ls -A "${VECTOR_DB_PATH}" 2>/dev/null)" ]; then
        echo "No vector database found. Starting initial sync in background..."
        
        # Start uvicorn in background first
        WORKERS=${NUM_OF_UVICORN_WORKERS:-4}
        echo "Starting server on 0.0.0.0:8000 with ${WORKERS} worker(s) in background..."
        uvicorn src.main:app \
            --host "0.0.0.0" \
            --port "8000" \
            --workers "${WORKERS}" \
            --loop uvloop \
            --limit-concurrency 40 &
        
        SERVER_PID=$!
        
        # Wait for server to be ready
        echo "Waiting for server to start..."
        sleep 10
        
        # Perform initial sync
        echo "Performing initial synchronization..."
        curl -X POST "http://localhost:8000/api/obs/sync?full_sync=true" || echo "Initial sync failed, but server is running"
        
        echo "Initial sync completed. Server is ready."
        
        # Wait for the server process
        wait $SERVER_PID
    else
        echo "Vector database exists. Skipping initial sync."
    fi
}

# Run initial sync if settings are provided
if [ -n "${OBSIDIAN_REPO_URL:-}" ] && [ -n "${VECTOR_DB_PATH:-}" ]; then
    perform_initial_sync
else
    echo "Obsidian settings not provided, skipping initial sync..."
fi

# --- Application startup ready ---
echo "Application startup preparations completed."

# --- Start Uvicorn server (or run another command) ---
# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    # Execute command as current user
    exec "$@"
else
    # If we reach here, initial sync was skipped (database already exists)
    # or we're running without Obsidian settings
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
