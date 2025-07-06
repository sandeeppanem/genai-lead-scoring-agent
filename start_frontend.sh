#!/bin/bash

echo "🚀 Starting GenAI Lead Scoring Assistant Frontend..."

# Check if we're in the right directory
if [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the development server
echo "🌐 Starting React development server..."
echo "   Frontend will be available at: http://localhost:3000"
echo "   Make sure the backend is running on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm start 