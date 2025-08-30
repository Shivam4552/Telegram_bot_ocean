# NEET Channel Moderation Bot

A Telegram bot designed to protect educational NEET channels from spam, vulgar content, competitor sabotage, and false reporting attempts.

## Features

### 🛡️ Content Protection
- **Vulgar Content Detection**: Automatically detects and removes inappropriate messages
- **Competitor Content Filtering**: Prevents promotional content from competing educational platforms
- **Screenshot Threat Prevention**: Identifies attempts to create fake screenshots for false reporting
- **Spam Pattern Recognition**: Blocks promotional messages and unwanted links

### 🖼️ Image Analysis
- **Screenshot Detection**: Identifies suspicious screenshot attempts
- **Image Content Analysis**: Analyzes uploaded images for inappropriate content
- **Document Filtering**: Processes image documents and files

### 👨‍💼 Admin Controls
- **Real-time Notifications**: Admins get instant alerts about violations
- **User Management**: Whitelist trusted users
- **Detailed Logging**: Complete audit trail of all moderation actions
- **Status Monitoring**: Check bot health and statistics

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Admin user IDs
- Channel/Group ID where bot will operate

### 2. Installation

```bash
# Clone or download the bot files
cd telegram_bot

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 3. Configuration

Edit the `.env` file with your details:

```env
BOT_TOKEN=your_telegram_bot_token_from_botfather
ADMIN_IDS=your admin id
CHANNEL_ID=channel id
LOG_LEVEL=INFO
```

**Getting Required IDs:**
- **Bot Token**: Message @BotFather on Telegram, create a new bot
- **Admin IDs**: Message @userinfobot to get your user ID
- **Channel ID**: Add @userinfobot to your channel, it will show the channel ID

### 4. Running the Bot

```bash
python moderation_bot.py
```

## Bot Commands

### Admin Commands
- `/start` - Initialize the bot
- `/help` - Show help message
- `/status` - Display bot status and statistics
- `/whitelist <user_id>` - Whitelist a trusted user

## Content Filtering Rules

### Blocked Content Types
1. **Vulgar/Inappropriate**: Spam, advertisements, inappropriate language
2. **Competitor References**: Names of competing educational platforms
3. **Screenshot Threats**: Messages indicating intent to create fake screenshots
4. **Spam Patterns**: Links, promotional content, contact requests

### Automatic Actions
- ❌ Delete violating messages
- ⚠️ Send warning to user
- 📨 Notify admins with violation details
- 📝 Log all actions for audit

## Customization

### Adding New Filter Words
Edit `config.py` and modify these lists:
- `VULGAR_WORDS`: Add inappropriate terms
- `COMPETITOR_KEYWORDS`: Add competitor names
- `SCREENSHOT_INDICATORS`: Add threat-related terms

### Adjusting Detection Sensitivity
Modify detection thresholds in:
- `content_filter.py`: Text analysis parameters
- `image_analyzer.py`: Image detection settings

## Security Features

### Protection Against False Reporting
- Detects messages with reporting intentions
- Prevents screenshot-based attacks
- Logs potential threats for investigation
- Automatic deletion of suspicious content

### Admin Security
- Only whitelisted admins can use commands
- Secure token management via environment variables
- Comprehensive audit logging

## Deployment

### Local Deployment
```bash
# Run directly
python moderation_bot.py

# Run with logging
python moderation_bot.py > bot.log 2>&1 &
```

### Production Deployment
1. Use a process manager like PM2 or systemd
2. Set up log rotation
3. Monitor bot health
4. Keep dependencies updated

## Troubleshooting

### Common Issues

**Bot not responding:**
- Check BOT_TOKEN is correct
- Verify bot has admin permissions in the channel
- Ensure bot is not muted

**Messages not being filtered:**
- Confirm CHANNEL_ID matches your channel
- Check if users are whitelisted
- Review filter word lists

**Image analysis not working:**
- Install OpenCV dependencies: `apt-get install python3-opencv`
- Check PIL/Pillow installation
- Verify image file permissions

### Log Analysis
The bot logs all activities. Check logs for:
- Filtering decisions
- Error messages
- Admin notifications
- User violations

## Support

For issues or improvements, check the bot logs and configuration settings. The bot is designed to be defensive and educational-focused, protecting your NEET preparation community from disruptive content.