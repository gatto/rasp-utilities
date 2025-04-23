#!/usr/bin/env fish

# Configuration - update these paths
set REPO_PATH "/home/fabio/repos/tulip"
set LOG_FILE "/home/fabio/local/logs/flask-apps-update.log"

# Change to repository directory
cd $REPO_PATH

# Get current commit hash
set CURRENT_HASH (git rev-parse HEAD)

# Use GitHub CLI to sync the repository (pulls latest changes)
gh repo sync >> $LOG_FILE 2>&1
if test $status -ne 0
    echo "Error syncing repository: $(date)" >> $LOG_FILE
    exit 1
end

# Get new commit hash
set NEW_HASH (git rev-parse HEAD)

# If the hash changed, update environment and restart services
if test "$CURRENT_HASH" != "$NEW_HASH"
    echo "New code detected, updating environment and restarting services: $(date)" >> $LOG_FILE
    
    # Update the environment with uv
    cd $REPO_PATH
    uv sync
    
    # Restart the services
    systemctl --user restart flask-client.service
    systemctl --user restart flask-server.service
    systemctl --user restart localtunnel.service
end
