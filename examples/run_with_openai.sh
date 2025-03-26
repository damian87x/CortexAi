#!/bin/bash
# Simple script to run the OpenAI provider with browser tool example

# Function to print colored text
print_color() {
  local color=$1
  local text=$2
  
  case $color in
    "red") echo -e "\033[0;31m$text\033[0m" ;;
    "green") echo -e "\033[0;32m$text\033[0m" ;;
    "blue") echo -e "\033[0;34m$text\033[0m" ;;
    "yellow") echo -e "\033[0;33m$text\033[0m" ;;
    *) echo "$text" ;;
  esac
}

print_color "blue" "======================================================"
print_color "blue" "      OpenAI Provider with Browser Tool Example"
print_color "blue" "======================================================"

# Check for dependencies
print_color "yellow" "Checking for dependencies..."

# Ensure pip is available
if ! command -v pip &> /dev/null; then
    print_color "red" "Error: pip is not installed."
    print_color "yellow" "Please install pip and try again."
    exit 1
fi

# Install required packages if not already installed
for package in openai tiktoken browser-use python-dotenv; do
    if ! pip show $package &> /dev/null; then
        print_color "yellow" "Installing $package..."
        pip install $package
    else
        print_color "green" "$package is already installed."
    fi
done

# Check for .env file
if [ ! -f ".env" ]; then
    print_color "yellow" "No .env file found. Creating one..."
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_color "yellow" "Created .env from .env.example template."
    else
        touch .env
        echo "# OpenAI API credentials" > .env
        echo "OPENAI_API_KEY=" >> .env
        print_color "yellow" "Created empty .env file."
    fi
    
    print_color "yellow" "Please add your OpenAI API key to the .env file."
    print_color "yellow" "Enter your OpenAI API key to add it to .env (or press Enter to skip):"
    read -s api_key
    
    if [ ! -z "$api_key" ]; then
        # Update the API key in the .env file
        if grep -q "OPENAI_API_KEY=" .env; then
            # Replace existing line
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=${api_key}/" .env
        else
            # Add new line
            echo "OPENAI_API_KEY=${api_key}" >> .env
        fi
        print_color "green" "API key added to .env file."
    else
        print_color "yellow" "No API key provided. You'll need to edit the .env file manually."
    fi
else
    print_color "green" ".env file already exists."
fi

# Run the example
print_color "yellow" "Running the OpenAI browser example..."
python examples/openai_browser_example.py

print_color "blue" "======================================================"
print_color "blue" "                     Finished"
print_color "blue" "======================================================"
