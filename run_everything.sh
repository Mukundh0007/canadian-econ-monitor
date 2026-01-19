#!/bin/bash

# run_everything.sh
# Automates the entire build and run process using usage of Docker.

echo "🚀 Starting Canadian Financial Data Pipeline..."
echo "------------------------------------------------"

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker Desktop and try again."
  exit 1
fi

echo "📦 Building and starting containers..."
echo "   - MySQL Database (waiting for healthcheck)"
echo "   - ETL Pipeline (runs once)"
echo "   - Streamlit Dashboard"
echo "------------------------------------------------"

# Build and Run
docker-compose up --build

# Use -d to run in background if preferred:
# docker-compose up --build -d
# echo "✅ Application running at http://localhost:8501"
