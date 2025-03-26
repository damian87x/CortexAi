#!/bin/bash
# Script to run CortexAi with either OpenAI or OpenRouter (Claude) providers

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

# Function to show help
show_help() {
  print_color "blue" "Usage: ./examples/run_with_llm.sh [options]"
  print_color "blue" "Options:"
  print_color "blue" "  -h, --help         Show this help message"
  print_color "blue" "  -p, --provider     Provider to use (openai or openrouter) - default: openrouter"
  print_color "blue" "  -m, --model        Model to use - default: anthropic/claude-3.7-sonnet:thinking for OpenRouter, gpt-4-turbo for OpenAI"
  print_color "blue" "  --headless         Run browser in headless mode (true/false) - default: true"
}

# Parse command line arguments
PROVIDER="openrouter"
MODEL=""
HEADLESS="true"

while [[ "$#" -gt 0 ]]; do
  case $1 in
    -h|--help) show_help; exit 0 ;;
    -p|--provider) PROVIDER="$2"; shift ;;
    -m|--model) MODEL="$2"; shift ;;
    --headless) HEADLESS="$2"; shift ;;
    *) print_color "red" "Unknown parameter: $1"; show_help; exit 1 ;;
  esac
  shift
done

# Validate provider
if [[ "$PROVIDER" != "openai" && "$PROVIDER" != "openrouter" ]]; then
  print_color "red" "Invalid provider: $PROVIDER. Must be 'openai' or 'openrouter'"
  exit 1
fi

print_color "blue" "======================================================"
print_color "blue" "      CortexAi with ${PROVIDER^^} Provider and Browser Tool"
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
for package in openai tiktoken browser-use python-dotenv requests; do
    if ! python3 -m pip show $package &> /dev/null; then
        print_color "yellow" "Installing $package..."
        python3 -m pip install $package
        
        # If we just installed browser-use, install Playwright browsers
        if [ "$package" = "browser-use" ]; then
            print_color "yellow" "Installing Playwright browsers for browser-use..."
            python3 -m playwright install
        fi
    else
        print_color "green" "$package is already installed."
        
        # Ensure Playwright browsers are installed even if browser-use is already installed
        if [ "$package" = "browser-use" ]; then
            # Check if we already have browsers installed
            if [ ! -d "$HOME/.cache/ms-playwright" ] || [ -z "$(ls -A $HOME/.cache/ms-playwright)" ]; then
                print_color "yellow" "Installing Playwright browsers for browser-use..."
                python3 -m playwright install
            else
                print_color "green" "Playwright browsers already installed."
            fi
        fi
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
        echo "# LLM provider API keys" > .env
        echo "OPENAI_API_KEY=" >> .env
        echo "OPENROUTER_API_KEY=" >> .env
        echo "" >> .env
        echo "# Browser tool configuration" >> .env
        echo "BROWSER_HEADLESS=$HEADLESS  # Headless mode is required if no X server is running" >> .env
        echo "BROWSER_DISABLE_SECURITY=true  # Security features disabled for automation" >> .env
        print_color "yellow" "Created empty .env file."
    fi
    
    print_color "yellow" "Please add your API keys to the .env file."
else
    print_color "green" ".env file already exists."
    
    # Update headless mode in .env if specified
    if grep -q "BROWSER_HEADLESS=" .env; then
        sed -i "s/BROWSER_HEADLESS=.*/BROWSER_HEADLESS=$HEADLESS/" .env
        print_color "yellow" "Updated BROWSER_HEADLESS=$HEADLESS in .env"
    else
        echo "BROWSER_HEADLESS=$HEADLESS" >> .env
        print_color "yellow" "Added BROWSER_HEADLESS=$HEADLESS to .env"
    fi
fi

# Set model in .env if provided
if [ ! -z "$MODEL" ]; then
    if grep -q "MODEL_NAME=" .env; then
        sed -i "s/MODEL_NAME=.*/MODEL_NAME=$MODEL/" .env
    else
        echo "MODEL_NAME=$MODEL" >> .env
    fi
    print_color "yellow" "Set MODEL_NAME=$MODEL in .env"
fi

# Run the appropriate example based on provider
print_color "yellow" "Running with $PROVIDER provider..."

if [ "$PROVIDER" = "openai" ]; then
    python3 examples/openai_browser_example.py
else
    python3 examples/openrouter_browser_example.py
fi

print_color "blue" "======================================================"
print_color "blue" "                     Finished"
print_color "blue" "======================================================"
