#!/bin/bash

echo "🚀 Starting Hybrid B2B Opportunity Prioritization Backend..."

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

# LLM explanations are optional and disabled by default. No API key is needed
# for scoring, deterministic explanations, or verified analytics.
if [ ! -f ".env" ]; then
    echo "ℹ️  No backend .env found; using the safe deterministic defaults."
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
