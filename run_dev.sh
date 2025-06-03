#!/bin/bash

# Extend Your Memory - Development Startup Script

echo "🚀 Starting Extend Your Memory Development Environment"
echo "======================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys before running again."
    echo "   Required: GOOGLE_API_KEY"
    echo "   Optional: GOOGLE_DRIVE_API_KEY, CHROME_API_KEY, MISTRAL_OCR_API_KEY"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "🐳 Starting services with Docker Compose..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

echo "🔍 Checking service status..."

# Check MCP Server
if curl -f http://localhost:8501/health > /dev/null 2>&1; then
    echo "✅ MCP Server is running (port 8501)"
else
    echo "❌ MCP Server is not responding"
fi

# Check Backend API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend API is running (port 8000)"
else
    echo "❌ Backend API is not responding"
fi

# Check Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running (port 3000)"
else
    echo "❌ Frontend is not responding"
fi

echo ""
echo "🌐 Application URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   MCP Server: http://localhost:8501"

echo ""
echo "🔧 To run comprehensive tests:"
echo "   python test_setup.py"

echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f [service-name]"
echo "   Services: mcp-server, backend, frontend"

echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"