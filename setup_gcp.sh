#!/bin/bash

# COlor codes
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Auto-Deployment on GCP...${NC}"

# 1. System Updates & Dependencies
echo -e "${GREEN}📦 Installing System Dependencies...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-venv unzip htop

# 2. Configure Swap (CRITICAL for e2-micro 1GB RAM)
if [ ! -f /swapfile ]; then
    echo -e "${GREEN}💾 Configuring 2GB Swap Memory...${NC}"
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    echo -e "${GREEN}✅ Swap already configured.${NC}"
fi

# 3. Set Timezone to IST
echo -e "${GREEN}tbl Setting Timezone to Asia/Kolkata...${NC}"
sudo timedatectl set-timezone Asia/Kolkata

# 4. Python Setup
echo -e "${GREEN}🐍 Setting up Python Environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Systemd Service Creation
echo -e "${GREEN}⚙️ Creating System Services...${NC}"

# Get current path
WD=$(pwd)
USER=$(whoami)

# Write Brain Service
sudo bash -c "cat > /etc/systemd/system/brain.service <<EOL
[Unit]
Description=Live Trading Brain
After=network.target

[Service]
User=$USER
WorkingDirectory=$WD
ExecStart=$WD/venv/bin/python3 live_brain.py
Restart=always
EnvironmentFile=$WD/.env

[Install]
WantedBy=multi-user.target
EOL"

# Write Scheduler Service
sudo bash -c "cat > /etc/systemd/system/scheduler.service <<EOL
[Unit]
Description=Whatsapp Scheduler
After=network.target

[Service]
User=$USER
WorkingDirectory=$WD
ExecStart=$WD/venv/bin/python3 notification_scheduler.py
Restart=always
EnvironmentFile=$WD/.env

[Install]
WantedBy=multi-user.target
EOL"

# 6. Final Instructions
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "---------------------------------------------------"
echo -e "👉 Step 1: Create your .env file now!"
echo -e "   Command: nano .env"
echo -e "   (Paste your tokens there)"
echo -e ""
echo -e "👉 Step 2: Start the bots"
echo -e "   Command: sudo systemctl enable --now brain scheduler"
echo -e "---------------------------------------------------"
