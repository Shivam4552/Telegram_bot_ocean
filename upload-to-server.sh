#!/bin/bash

# Upload bot files to Digital Ocean droplet
# Usage: ./upload-to-server.sh your_droplet_ip [username]

if [ $# -eq 0 ]; then
    echo "Usage: $0 <droplet_ip> [username]"
    echo "Example: $0 192.168.1.100 root"
    echo "Example: $0 192.168.1.100 ubuntu"
    exit 1
fi

DROPLET_IP=$1
USERNAME=${2:-root}
BOT_DIR="/home/$USERNAME/telegram_bot"

# If username is root, use /root instead
if [ "$USERNAME" = "root" ]; then
    BOT_DIR="/root/telegram_bot"
fi

echo "🚀 Uploading Telegram Bot to Digital Ocean..."
echo "📡 Target: $USERNAME@$DROPLET_IP:$BOT_DIR"

# Create directory on server
ssh $USERNAME@$DROPLET_IP "mkdir -p $BOT_DIR"

# Upload all files except sensitive ones
rsync -avz --progress \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs' \
    --exclude='.gitignore' \
    ./ $USERNAME@$DROPLET_IP:$BOT_DIR/

echo "✅ Files uploaded successfully!"
echo ""
echo "📋 Next steps:"
echo "1. SSH to your server: ssh $USERNAME@$DROPLET_IP"
echo "2. Run setup script: cd $BOT_DIR && ./setup_server.sh"
echo "3. Configure your bot token and settings in .env file"
echo "4. The bot will be set up as a systemd service and start automatically"