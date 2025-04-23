#!/usr/bin/env fish

# Activate Node v23
nvm use v23 >/dev/null 2>&1

# Run localtunnel (using the lt command which is now available in PATH)
lt --port 5001 --subdomain tulipgatto
