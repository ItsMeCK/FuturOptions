#!/bin/bash

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}🔄 Updating Bot to Latest 'Carrier Class' Version...${NC}"

# 1. Pull Latest Code
git pull

# 2. Restart Services (Uses sudo as systemctl needs it)
echo -e "${GREEN}⚙️ Restarting Services...${NC}"
sudo systemctl restart brain
sudo systemctl restart scheduler
sudo systemctl restart token_ui

# 3. Check Status
echo -e "${GREEN}📊 Current Status:${NC}"
sudo systemctl status brain --no-pager | grep "Active:"
echo -e "${GREEN}✅ System Updated and Running!${NC}"
