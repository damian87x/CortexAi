#!/bin/bash
# Setup script for CortexAi development environment

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up CortexAi development environment...${NC}"

if ! dpkg -l | grep -q python3-venv; then
    echo -e "${YELLOW}Python virtual environment package not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-full
fi

if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip

echo -e "${GREEN}Installing package in development mode...${NC}"
pip install -e .

echo -e "${GREEN}Installing optional dependencies...${NC}"
pip install -e ".[yaml,dev]"

if [ ! -f "CortexAi/config/.env" ] && [ -f "CortexAi/config/.env.template" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp CortexAi/config/.env.template CortexAi/config/.env
    echo -e "${YELLOW}Please edit CortexAi/config/.env with your actual configuration values.${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}To activate the environment, run:${NC}"
echo -e "    source venv/bin/activate"
echo -e "${YELLOW}To deactivate the environment, run:${NC}"
echo -e "    deactivate"
