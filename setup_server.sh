#!/bin/bash

# Digital Ocean Droplet Setup Script for Telegram Bot
# Run this script on your Digital Ocean droplet after creating it

set -e

echo "🚀 Setting up Telegram Bot on Digital Ocean Droplet..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python 3 and pip
echo "🐍 Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv git curl

# Install system dependencies for OpenCV and image processing
echo "📸 Installing system dependencies for image processing..."
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 libglib2.0-0 libgtk-3-0

# Create project directory
PROJECT_DIR="/opt/telegram_bot"
echo "📁 Creating project directory at $PROJECT_DIR..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Copy project files (assumes files are uploaded to home directory)
if [ -d "$HOME/telegram_bot" ]; then
    echo "📋 Copying project files..."
    cp -r $HOME/telegram_bot/* $PROJECT_DIR/
    cd $PROJECT_DIR
else
    echo "❌ Project files not found in $HOME/telegram_bot"
    echo "Please upload your project files to the home directory first"
    exit 1
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Create systemd service file
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Moderation Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/run.py
Restart=always
RestartSec=10
Environment=PATH=$PROJECT_DIR/venv/bin

[Install]
WantedBy=multi-user.target
EOF

# Create environment file template
echo "📝 Creating environment file template..."
tee $PROJECT_DIR/.env.example > /dev/null <<EOF
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_admin_user_ids_comma_separated
CHANNEL_ID=your_channel_id_here
LOG_LEVEL=INFO
EOF

echo "✅ Server setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Copy .env.example to .env: cp .env.example .env"
echo "2. Edit .env file with your actual values: nano .env"
echo "3. Enable and start the service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable telegram-bot"
echo "   sudo systemctl start telegram-bot"
echo "4. Check service status: sudo systemctl status telegram-bot"
echo "5. View logs: sudo journalctl -u telegram-bot -f"
echo ""
echo "🔧 Useful commands:"
echo "- Restart bot: sudo systemctl restart telegram-bot"
echo "- Stop bot: sudo systemctl stop telegram-bot"
echo "- View logs: sudo journalctl -u telegram-bot -n 50"