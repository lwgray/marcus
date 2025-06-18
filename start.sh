#!/bin/bash
# PM Agent Easy Start Script

echo "🚀 PM Agent - Easy Docker Setup"
echo "================================"

# Check deployment type
if [ "$1" = "remote" ] || [ "$DEPLOYMENT" = "remote" ]; then
    echo "🌐 REMOTE DEPLOYMENT MODE"
    echo "⚠️  Planka is NOT available in remote deployments due to licensing"
    echo ""
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    
    if [ "$1" = "remote" ] || [ "$DEPLOYMENT" = "remote" ]; then
        # Remote deployment template (no Planka)
        cat > .env << EOF
# Kanban Provider (github or linear ONLY for remote deployment)
KANBAN_PROVIDER=github

# GitHub Configuration (Recommended for remote)
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_repo_name

# Linear Configuration (Alternative for remote)
LINEAR_API_KEY=your_linear_api_key
LINEAR_TEAM_ID=your_linear_team_id

# AI Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Security (for remote deployment)
MCP_AUTH_TOKENS=token1,token2,token3
EOF
    else
        # Local deployment template (all providers available)
        cat > .env << EOF
# Kanban Provider (github, linear, or planka)
KANBAN_PROVIDER=github

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_repo_name

# Linear Configuration (if using Linear)
LINEAR_API_KEY=your_linear_api_key
LINEAR_TEAM_ID=your_linear_team_id

# Planka Configuration (LOCAL USE ONLY)
PLANKA_PROJECT_NAME=your_planka_project
PLANKA_SECRET_KEY=your-secret-key

# AI Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
EOF
    fi
    
    echo "✅ .env file created. Please edit it with your API keys!"
    echo ""
fi

# Parse command line arguments
MODE="basic"
if [ "$1" = "demo" ]; then
    MODE="demo"
elif [ "$1" = "full" ]; then
    MODE="full"
elif [ "$1" = "dev" ]; then
    MODE="dev"
elif [ "$1" = "local-planka" ]; then
    MODE="local-planka"
elif [ "$1" = "remote" ]; then
    MODE="remote"
fi

echo "🔧 Starting PM Agent in $MODE mode..."
echo ""

case $MODE in
    "basic")
        echo "📦 Starting core PM Agent only..."
        docker-compose up -d pm-agent
        ;;
    "demo")
        echo "📦 Starting PM Agent with demo workers..."
        docker-compose --profile demo up -d
        ;;
    "full")
        echo "📦 Starting PM Agent with visualization UI..."
        docker-compose --profile full up -d
        ;;
    "dev")
        echo "📦 Starting PM Agent in development mode..."
        docker-compose up -d pm-agent-dev
        ;;
    "local-planka")
        echo "📦 Starting PM Agent with LOCAL Planka..."
        echo "⚠️  WARNING: Planka is AGPL licensed - for personal/local use only!"
        echo ""
        # Check if KANBAN_PROVIDER is set to planka
        if grep -q "KANBAN_PROVIDER=planka" .env 2>/dev/null; then
            docker-compose --profile local-planka up -d pm-agent planka planka-db
        else
            echo "❌ Error: KANBAN_PROVIDER must be set to 'planka' in .env"
            echo "Please edit .env and set: KANBAN_PROVIDER=planka"
            exit 1
        fi
        ;;
    "remote")
        echo "🌐 Starting PM Agent for REMOTE deployment..."
        echo "⚠️  Using remote-safe configuration (no Planka)"
        docker-compose -f docker-compose.remote.yml up -d
        ;;
esac

echo ""
echo "✅ PM Agent is starting up!"
echo ""
echo "📋 Available commands:"
echo "  ./start.sh              - Start core PM Agent only (GitHub/Linear)"
echo "  ./start.sh demo         - Start with demo workers"
echo "  ./start.sh full         - Start with visualization UI"
echo "  ./start.sh dev          - Start in development mode"
echo "  ./start.sh local-planka - Start with Planka (LOCAL USE ONLY)"
echo "  ./start.sh remote       - Start for remote deployment (no Planka)"
echo ""
echo "📊 View logs:"
echo "  docker-compose logs -f pm-agent"
echo ""
echo "🛑 Stop everything:"
echo "  docker-compose down"
echo ""

if [ "$MODE" = "full" ]; then
    echo "🌐 Visualization UI will be available at:"
    echo "  http://localhost:4298"
    echo ""
fi

if [ "$MODE" = "local-planka" ]; then
    echo "🎯 Planka will be available at:"
    echo "  http://localhost:1337"
    echo "  ⚠️  Remember: Planka is for LOCAL USE ONLY due to AGPL license"
    echo ""
fi

if [ "$MODE" = "remote" ]; then
    echo "🌐 Remote MCP endpoint available at:"
    echo "  http://localhost:8000/sse"
    echo "  Configure your MCP client with appropriate auth tokens"
    echo ""
fi