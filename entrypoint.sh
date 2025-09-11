#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# --- Clone/Update Obsidian Repository ---
clone_obsidian_repo() {
    echo "Setting up Obsidian repository..."
    
    # Remove existing directory if it exists
    if [ -d "${OBSIDIAN_LOCAL_PATH}" ]; then
        echo "Removing existing directory: ${OBSIDIAN_LOCAL_PATH}"
        rm -rf "${OBSIDIAN_LOCAL_PATH}"
    fi
    
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
    
    # Clone repository
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

# Clone Obsidian repo if settings are provided
if [ -n "${OBSIDIAN_REPO_URL:-}" ] && [ -n "${OBSIDIAN_LOCAL_PATH:-}" ]; then
    clone_obsidian_repo
else
    echo "Obsidian settings not provided, skipping repository clone..."
fi

# --- Application startup ready ---
echo "Application startup preparations completed."

# --- Start Uvicorn server (or run another command) ---
# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    WORKERS=${NUM_OF_UVICORN_WORKERS:-4}
    echo "Starting server on 0.0.0.0:8000 with ${WORKERS} worker(s)..."
    exec uvicorn src.main:app \
        --host "0.0.0.0" \
        --port "8000" \
        --workers "${WORKERS}" \
        --loop uvloop \
        --limit-concurrency 40
fi
