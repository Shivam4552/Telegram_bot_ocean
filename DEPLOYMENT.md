# Digital Ocean Droplet Deployment Guide

## Prerequisites

1. **Digital Ocean Account** with billing enabled
2. **Bot Token** from @BotFather
3. **Admin IDs** and **Channel ID**
4. **SSH access** to your droplet

## Step-by-Step Deployment

### 1. Create Digital Ocean Droplet

1. **Login to Digital Ocean Console**
2. **Create Droplet**:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic plan, $6/month (1GB RAM, 1 vCPU)
   - **Datacenter**: Choose closest to your location
   - **Authentication**: SSH keys (recommended) or password
   - **Hostname**: `telegram-bot-server`

### 2. Upload Bot Files to Droplet

From your local machine, run:

```bash
# Make upload script executable
chmod +x upload-to-server.sh

# Upload to droplet (replace with your droplet IP)
./upload-to-server.sh YOUR_DROPLET_IP root
# or for ubuntu user: ./upload-to-server.sh YOUR_DROPLET_IP ubuntu
```

### 3. SSH to Your Droplet and Run Setup

```bash
# SSH to your droplet (replace IP with your droplet's IP)
ssh root@your_droplet_ip

# Navigate to bot directory
cd telegram_bot

# Run setup script (this installs Python, dependencies, and sets up the service)
./setup_server.sh
```

### 4. Configure Environment Variables

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Edit .env with your actual values:**
```env
BOT_TOKEN=your_actual_bot_token_here
ADMIN_IDS=your_admin_user_ids_comma_separated
CHANNEL_ID=your_channel_id_here
LOG_LEVEL=INFO
```

### 5. Start the Bot Service

```bash
# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Check if bot is running
sudo systemctl status telegram-bot
```

### 6. Monitor the Bot

```bash
# Check bot logs (live)
sudo journalctl -u telegram-bot -f

# Check last 50 log entries
sudo journalctl -u telegram-bot -n 50

# Check service status
sudo systemctl status telegram-bot
```

## Management Commands

### Start/Stop Bot
```bash
# Start bot
sudo systemctl start telegram-bot

# Stop bot
sudo systemctl stop telegram-bot

# Restart bot
sudo systemctl restart telegram-bot

# Enable auto-start on boot
sudo systemctl enable telegram-bot

# Disable auto-start on boot
sudo systemctl disable telegram-bot
```

### View Logs
```bash
# Live logs
sudo journalctl -u telegram-bot -f

# Last 100 lines
sudo journalctl -u telegram-bot -n 100

# Logs from today
sudo journalctl -u telegram-bot --since today
```

### Update Bot
```bash
# Navigate to bot directory
cd /opt/telegram_bot

# Update code (if using git)
git pull

# Restart service to apply changes
sudo systemctl restart telegram-bot
```

## Troubleshooting

### Bot Not Starting
```bash
# Check service status
sudo systemctl status telegram-bot

# Check logs for errors
sudo journalctl -u telegram-bot -n 50

# Check system resources
free -h
df -h
```

### Bot Not Responding
1. **Check bot token** in .env file
2. **Verify network connectivity**:
   ```bash
   curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe
   ```
3. **Check if bot is admin** in your channel
4. **Verify environment variables are loaded**:
   ```bash
   sudo systemctl show telegram-bot -p Environment
   ```

### Performance Issues
- **Upgrade droplet** if CPU/RAM usage is high
- **Monitor logs** for error patterns
- **Check system resources**: `htop` or `top`

## Security Best Practices

1. **Firewall Setup**:
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   sudo ufw allow 22/tcp
   ```

2. **Regular Updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Monitor Resource Usage**:
   ```bash
   htop
   free -h
   df -h
   ```

4. **Secure Environment File**:
   ```bash
   chmod 600 .env
   ```

## Cost Estimation

- **Basic Droplet**: $6/month (1GB RAM, 1 vCPU, 25GB SSD)
- **Bandwidth**: 1TB included
- **Total**: ~$6/month

## Support

For issues:
1. Check service logs: `sudo journalctl -u telegram-bot -f`
2. Verify configuration in `.env`
3. Test bot token: `curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe`
4. Ensure bot has admin rights in channel
5. Check service status: `sudo systemctl status telegram-bot`