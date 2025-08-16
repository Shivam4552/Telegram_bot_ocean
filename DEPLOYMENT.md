# Digital Ocean Deployment Guide

## Prerequisites

1. **Digital Ocean Account** with billing enabled
2. **Docker** and **Docker Compose** installed on your droplet
3. **Bot Token** from @BotFather
4. **Admin IDs** and **Channel ID**

## Step-by-Step Deployment

### 1. Create Digital Ocean Droplet

1. **Login to Digital Ocean Console**
2. **Create Droplet**:
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic plan, $6/month (1GB RAM, 1 vCPU)
   - **Datacenter**: Choose closest to your location
   - **Authentication**: SSH keys (recommended) or password
   - **Hostname**: `neet-telegram-bot`

### 2. Connect to Your Droplet

```bash
# SSH to your droplet (replace IP with your droplet's IP)
ssh root@your_droplet_ip
```

### 3. Install Docker and Docker Compose

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Enable Docker to start on boot
systemctl enable docker
systemctl start docker
```

### 4. Upload Bot Files

**Option A: Direct Upload**
```bash
# Create directory
mkdir -p /root/telegram_bot
cd /root/telegram_bot

# Upload files using scp from your local machine
# scp -r /home/shivam/Desktop/telegram_bot/* root@your_droplet_ip:/root/telegram_bot/
```

**Option B: Git Repository**
```bash
# If you have the code in a git repository
git clone your_repository_url
cd telegram_bot
```

### 5. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Edit .env with your actual values:**
```env
BOT_TOKEN=7543908745:AAH4k7_N_JnFtRB6BL0vPXF9q4_apnUzVFY
ADMIN_IDS=1295934129
CHANNEL_ID=-1002738733550
LOG_LEVEL=INFO
```

### 6. Deploy the Bot

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### 7. Monitor the Bot

```bash
# Check bot logs
docker-compose logs -f

# Check bot status
docker-compose ps

# Restart bot if needed
docker-compose restart
```

## Management Commands

### Start/Stop Bot
```bash
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# Restart bot
docker-compose restart
```

### View Logs
```bash
# Live logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Update Bot
```bash
# Pull latest changes (if using git)
git pull

# Rebuild and restart
./deploy.sh
```

## Troubleshooting

### Bot Not Starting
```bash
# Check logs for errors
docker-compose logs

# Check if container is running
docker ps

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

### Performance Issues
- **Upgrade droplet** if CPU/RAM usage is high
- **Monitor logs** for error patterns
- **Check Docker stats**: `docker stats`

## Security Best Practices

1. **Firewall Setup**:
   ```bash
   ufw enable
   ufw allow ssh
   ufw allow 80
   ufw allow 443
   ```

2. **Regular Updates**:
   ```bash
   apt update && apt upgrade -y
   ```

3. **Monitor Resource Usage**:
   ```bash
   htop
   docker stats
   ```

## Cost Estimation

- **Basic Droplet**: $6/month (1GB RAM, 1 vCPU)
- **Storage**: Included (25GB SSD)
- **Bandwidth**: 1TB included
- **Total**: ~$6-8/month

## Support

For issues:
1. Check bot logs: `docker-compose logs`
2. Verify configuration in `.env`
3. Test bot token: `curl -s https://api.telegram.org/bot$BOT_TOKEN/getMe`
4. Ensure bot has admin rights in channel