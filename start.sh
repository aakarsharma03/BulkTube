#!/bin/bash

# BulkTube Startup Script

# 1. Navigate to the directory of this script (ensures relative paths work)
cd "$(dirname "$0")"

echo "🚀 Starting BulkTube..."

# 2. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in your PATH."
    exit 1
fi

# 3. Install/Update Dependencies
echo "📦 Checking and installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Failed to install dependencies. Trying to run anyway..."
fi

# 4. Run the Flask App
echo "==================================================="
echo "🟢 Server starting..."
echo "👉 Open in your browser: http://127.0.0.1:5001"
echo "==================================================="

python3 app.py
