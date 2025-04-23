#!/usr/bin/env fish

# Configuration - update these paths
set REPO_PATH "/home/fabio/repos/tulip"
set LOG_FILE "/var/log/flask-apps-update.log"

# Change to repository directory
cd $REPO_PATH

# Use GitHub CLI to sync the repository (pulls latest changes)
gh repo sync >> $LOG_FILE 2>&1
if test $status -ne 0
    echo "Error syncing repository: $(date)" >> $LOG_FILE
    exit 1
end
