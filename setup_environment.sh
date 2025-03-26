#!/bin/bash

set -e  # Exit on error

echo "=== Setting up Python environment for CortexAi ==="
echo

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -U python-dotenv requests playwright browser-use

# Install additional dependencies for the project
echo "Installing additional dependencies..."
pip install openai aiohttp tenacity

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install

# Check package installation
echo "\nVerifying installed packages:"
pip list | grep -E "dotenv|requests|playwright|browser-use|openai|aiohttp|tenacity"

# Create or update .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.sample..."
    cp .env.sample .env
    echo "Please update your API keys in the .env file."
else 
    echo ".env file already exists."
fi

echo ""
echo "=== Setup completed ==="
echo "To activate this environment in the future, run:"
echo "source venv/bin/activate"
echo ""
echo "To run the browser test, use:"
echo "source venv/bin/activate && python browser_click_test.py"
echo ""
echo "To use the improved flow with CortexAI, run:"
echo "source venv/bin/activate && python improved_run_flow.py"
echo ""
