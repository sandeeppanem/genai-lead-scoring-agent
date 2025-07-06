#!/bin/bash

echo "🚀 Starting GenAI Lead Scoring Assistant Backend..."

# Check if we're in the right directory
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Navigate to backend directory
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Please create one with your Anthropic API key."
    echo "   Copy env.example to .env and add your ANTHROPIC_API_KEY"
fi

# Start the server
echo "🌐 Starting FastAPI server..."
echo "   Frontend will be available at: http://localhost:3000"
echo "   Backend API will be available at: http://localhost:8000"
echo "   API Documentation will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 