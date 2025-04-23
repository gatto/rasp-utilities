#!/usr/bin/env fish

# Configuration - update these paths
set REPO_PATH "/users/fabio/repos/tulip"
set LOG_FILE "/var/log/tulip-repo-update.log"

# Change to repository directory
cd $REPO_PATH

# Run git pull with error handling
git pull >> $LOG_FILE 2>&1
if test $status -ne 0
    echo "Error pulling from repository: $(date)" >> $LOG_FILE
    exit 1
end
