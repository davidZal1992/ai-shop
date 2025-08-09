#!/bin/bash
# Setup script for AI Shopping System

echo "🚀 Setting up AI Shopping System..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Create environment file template
echo "⚙️ Creating environment file template..."
cat > .env << 'ENVEOF'
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Crawler Server Configuration
CRAWLER_SERVER_URL=http://localhost:8000

# Optional: Logging Level
LOG_LEVEL=INFO
ENVEOF

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your OpenAI API key"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Start crawler server: cd crawler-server && uvicorn main:app --reload"
echo "4. In another terminal, run agent: cd agent && python shopping_agent.py"
echo ""
echo "🔗 Server will be available at: http://localhost:8000"
