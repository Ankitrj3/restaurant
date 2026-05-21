#!/usr/bin/env bash

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Read FLASK_PORT from .env, fallback to 5050 if not found
PORT=$(grep -E "^FLASK_PORT=" .env | cut -d'=' -f2 | tr -d '\r ')
if [ -z "$PORT" ]; then
  PORT=5050
fi

# Detect OS type
IS_WINDOWS=false
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" || "$OSTYPE" == "windows" ]]; then
  IS_WINDOWS=true
fi

start_service() {
  echo "=== Starting Restaurant Pricing Intelligence Platform ==="
  echo "Detecting environment..."
  
  # Activate virtual environment based on OS
  if [ "$IS_WINDOWS" = true ]; then
    if [ -f "venv/Scripts/activate" ]; then
      echo "Activating Windows virtual environment..."
      source venv/Scripts/activate
    else
      echo "Warning: venv/Scripts/activate not found. Attempting to run with system python..."
    fi
  else
    if [ -f "venv/bin/activate" ]; then
      echo "Activating macOS/Linux virtual environment..."
      source venv/bin/activate
    else
      echo "Warning: venv/bin/activate not found. Attempting to run with system python..."
    fi
  fi

  # Start the server
  echo "Starting Flask server on port $PORT..."
  cd backend
  if [ "$IS_WINDOWS" = true ]; then
    python app.py
  else
    python3 app.py
  fi
}

stop_service() {
  echo "=== Stopping service on port $PORT ==="
  
  if [ "$IS_WINDOWS" = true ]; then
    # Windows stop command
    PID=$(netstat -ano | grep LISTENING | grep ":$PORT" | awk '{print $5}' | head -n 1 | tr -d '\r ')
    if [ -n "$PID" ]; then
      echo "Found process running on port $PORT (PID: $PID). Killing process..."
      taskkill //F //PID "$PID"
      echo "Service stopped successfully."
    else
      echo "No service found running on port $PORT."
    fi
  else
    # macOS/Linux stop command
    PID=$(lsof -t -i :"$PORT")
    if [ -n "$PID" ]; then
      echo "Found process running on port $PORT (PID: $PID). Killing process..."
      kill -9 $PID
      echo "Service stopped successfully."
    else
      echo "No service found running on port $PORT."
    fi
  fi
}

# Parse command line argument
case "$1" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  restart)
    stop_service
    sleep 2
    start_service
    ;;
  *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac
