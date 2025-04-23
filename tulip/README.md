This:
- Uses systemd to ensure your Flask apps and localtunnel stay running
- Automatically pulls from your private GitHub repo every 5 minutes
- Uses uv for Python environment management
- Updates dependencies and restarts services when new code is detected

## Setup Instructions

1. First, make sure you have SSH key authentication set up for your private GitHub repository:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Add the public key to your GitHub account
```

2. Clone your repository:

```bash
git clone git@github.com:yourusername/your-private-repo.git /path/to/your/repo
```

3. Set up uv for Python environment management:

```bash
# Install uv if not already installed
pip install uv

# Create and activate a virtual environment
cd /path/to/your/repo
uv venv /path/to/uv_folder
```

4. Create directories for systemd user services:

```bash
mkdir -p ~/.config/systemd/user
```

5. Create all the files mentioned above

6. Enable and start the services:

```bash
# Enable lingering to allow user services to run after logout
loginctl enable-linger $USER

# Enable and start the services
systemctl --user daemon-reload
systemctl --user enable flask-client.service
systemctl --user enable flask-server.service
systemctl --user enable localtunnel.service
systemctl --user enable check-flask-updates.timer

systemctl --user start flask-client.service
systemctl --user start flask-server.service
systemctl --user start localtunnel.service
systemctl --user start check-flask-updates.timer
```

### Verifying the Setup

Check if services are running:

```bash
systemctl --user status flask-client.service
systemctl --user status flask-server.service
systemctl --user status localtunnel.service
systemctl --user status check-flask-updates.timer
```

View logs for any service:

```bash
journalctl --user -u flask-client.service
```
