#!/bin/bash
# Texie Setup Script
# Run this once to install dependencies and configure the environment.

set -e

echo "══════════════════════════════════════════"
echo "  Texie — Private Messenger Setup"
echo "══════════════════════════════════════════"

# Check Python version
python3 --version || { echo "Python 3 required"; exit 1; }

# Install dependencies
echo ""
echo "→ Installing Python dependencies..."
pip3 install -r requirements.txt

# Create backend .env from example if not exists
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo ""
    echo "→ Created backend/.env — EDIT THIS FILE with your settings!"
    echo "   • Set USER_A_PASSWORD and USER_B_PASSWORD"
    echo "   • Set SECRET_KEY to a random 32-byte hex string"
    echo "   • Set DATABASE_URL to your PostgreSQL connection string"
fi

# Docker Compose setup
echo ""
echo "→ Starting PostgreSQL with Docker..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d postgres
    echo "   PostgreSQL started on port 5432"
else
    echo "   Docker not found. Start PostgreSQL manually."
    echo "   Then set DATABASE_URL in backend/.env"
fi

echo ""
echo "══════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  To run the backend:"
echo "    python -m backend.main"
echo ""
echo "  To run the mobile app:"
echo "    python main.py"
echo ""
echo "  Secret sequence to unlock chat: 7 → 3 → 9 → 1 → ="
echo "══════════════════════════════════════════"
