#!/bin/bash

# Docker Setup Script for Extend Your Memory

echo "🐳 Docker Setup for Extend Your Memory"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo "💡 Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check current user's Docker permissions
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker permission issue detected."
    echo ""
    echo "🔧 Fixing Docker permissions..."
    
    # Add user to docker group
    echo "Adding user $USER to docker group..."
    sudo usermod -aG docker $USER
    
    echo "✅ User added to docker group."
    echo ""
    echo "🔄 Please log out and log back in, then run this script again."
    echo "   Or run: newgrp docker"
    echo ""
    echo "💡 Alternative: Run with sudo:"
    echo "   sudo docker compose up --build"
    exit 0
fi

echo "✅ Docker is properly configured!"
echo ""

# Check Docker Compose
if ! docker compose version > /dev/null 2>&1; then
    echo "⚠️  Docker Compose V2 not available, trying legacy docker-compose..."
    if ! docker-compose --version > /dev/null 2>&1; then
        echo "❌ Docker Compose is not installed."
        echo "💡 Please install Docker Compose:"
        echo "   https://docs.docker.com/compose/install/"
        exit 1
    else
        echo "✅ Using legacy docker-compose"
        COMPOSE_CMD="docker-compose"
    fi
else
    echo "✅ Using Docker Compose V2"
    COMPOSE_CMD="docker compose"
fi

echo ""
echo "🚀 Ready to start Extend Your Memory!"
echo "Run: ./run_dev.sh"