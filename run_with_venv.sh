#!/bin/bash

# Set script to exit on error
set -e

echo "=== Running CortexAi with virtual environment ==="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install python-dotenv requests playwright browser-use openai aiohttp tenacity
    python -m playwright install
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.sample" ]; then
        echo "Creating .env file from .env.sample..."
        cp .env.sample .env
        echo "Please update your API keys in the .env file."
    else
        echo "No .env file found. Please create one with your API keys."
        exit 1
    fi
fi

# Run the improved flow script
echo "Running improved_run_flow.py with virtual environment..."
python improved_run_flow.py "$@"
