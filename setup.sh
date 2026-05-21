#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting Restaurant Pricing Platform Setup"
echo "=========================================================="

# 1. Check Python installation
echo "Checking for Python 3..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Verify it is python 3
    VERSION=$(python --version 2>&1 | awk '{print $2}')
    if [[ "$VERSION" == 3* ]]; then
        PYTHON_CMD="python"
    else
        echo "Error: Python 3 is required. Found Python $VERSION"
        exit 1
    fi
else
    echo "Error: Python 3 is not installed on this system."
    echo "Please install Python 3 from https://www.python.org/downloads/ and try again."
    exit 1
fi

echo "Using Python command: $PYTHON_CMD ($($PYTHON_CMD --version))"

# 2. Create virtual environment
echo "Creating python virtual environment (venv)..."
if [ -d "venv" ]; then
    echo "Virtual environment 'venv' already exists. Skipping creation."
else
    $PYTHON_CMD -m venv venv
    echo "Virtual environment created successfully."
fi

# 3. Detect OS and Activate venv
IS_WINDOWS=false
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" || "$OSTYPE" == "windows" ]]; then
  IS_WINDOWS=true
fi

if [ "$IS_WINDOWS" = true ]; then
    echo "Activating Windows virtual environment..."
    source venv/Scripts/activate
else
    echo "Activating macOS/Linux virtual environment..."
    source venv/bin/activate
fi

# 4. Install dependencies
echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing project dependencies from backend/requirements.txt..."
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
else
    echo "Error: backend/requirements.txt not found!"
    exit 1
fi

# 5. Create .env if it does not exist
echo "Checking environment variables..."
if [ -f ".env" ]; then
    echo ".env file already exists. Keeping current configuration."
else
    echo "Creating default .env file..."
    cat <<EOT > .env
# ===========================================
# Restaurant Competitor Intelligence Platform
# Environment Configuration
# ===========================================

# Claude API
ANTHROPIC_API_KEY=

# Gemini API
GEMINI_API_KEY=

# GraphHopper API
GRAPHHOPPER_API_KEY=

# PostgreSQL Database
DATABASE_URL=postgresql://postgres:restaurant123@localhost:5433/restaurant_intel
DB_HOST=localhost
DB_PORT=5433
DB_NAME=restaurant_intel
DB_USER=postgres
DB_PASSWORD=restaurant123

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_PORT=5050
SECRET_KEY=your-secret-key-change-in-production

# Client Restaurant Configuration
CLIENT_RESTAURANT_NAME=Bawarchi Indian Cuisine & Bar Leander
CLIENT_RESTAURANT_ADDRESS=15881 Ronald Reagan Blvd #5, Leander, TX 78641, United States
CLIENT_LAT=30.5680447
CLIENT_LNG=-97.8029374

# Search Configuration
INITIAL_SEARCH_RADIUS_MILES=3
MAX_SEARCH_RADIUS_MILES=20
MIN_COMPETITORS=5
EOT
    echo ".env file created. Please open it and add your Gemini/Claude API Keys."
fi

# 6. Make control script executable
if [ -f "service.sh" ]; then
    chmod +x service.sh
fi

echo "=========================================================="
echo " Setup Completed Successfully!"
echo "=========================================================="
echo "To manage your service, run:"
echo "  Start:   ./service.sh start"
echo "  Stop:    ./service.sh stop"
echo "  Restart: ./service.sh restart"
echo "=========================================================="
EOT
