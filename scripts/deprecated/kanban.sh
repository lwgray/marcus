#!/bin/bash
# Kanban MCP Server Manager (Shell Version)

KANBAN_MCP_PATH="/Users/lwgray/dev/kanban-mcp"
PID_FILE="$HOME/.kanban-mcp.pid"
LOG_FILE="$HOME/.kanban-mcp.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Functions
start_server() {
    echo -e "${BLUE}🚀 Starting kanban-mcp server...${NC}"
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  kanban-mcp is already running (PID: $PID)${NC}"
            return
        fi
    fi
    
    # Check if kanban-mcp exists
    if [ ! -f "$KANBAN_MCP_PATH/dist/index.js" ]; then
        echo -e "${RED}❌ kanban-mcp not found at $KANBAN_MCP_PATH${NC}"
        exit 1
    fi
    
    # Start the server
    cd "$KANBAN_MCP_PATH"
    PLANKA_BASE_URL="http://localhost:3333" \
    PLANKA_AGENT_EMAIL="demo@demo.demo" \
    PLANKA_AGENT_PASSWORD="demo" \
    nohup node dist/index.js > "$LOG_FILE" 2>&1 &
    
    PID=$!
    echo $PID > "$PID_FILE"
    
    sleep 2
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ kanban-mcp started successfully (PID: $PID)${NC}"
        echo "  📄 Log file: $LOG_FILE"
    else
        echo -e "${RED}❌ Failed to start kanban-mcp${NC}"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop_server() {
    echo -e "${BLUE}🛑 Stopping kanban-mcp server...${NC}"
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}⚠️  kanban-mcp is not running (no PID file)${NC}"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
        fi
        
        echo -e "${GREEN}✅ kanban-mcp stopped successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  kanban-mcp is not running (process not found)${NC}"
    fi
    
    rm -f "$PID_FILE"
}

server_status() {
    echo -e "${BLUE}📊 kanban-mcp Status${NC}"
    echo "========================================"
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}❌ kanban-mcp is not running (no PID file)${NC}"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ kanban-mcp is running${NC}"
        echo "  PID: $PID"
        echo "  Process: $(ps -p $PID -o comm=)"
        
        if [ -f "$LOG_FILE" ]; then
            echo -e "\n${BLUE}Recent log entries:${NC}"
            tail -n 5 "$LOG_FILE" | sed 's/^/  /'
        fi
    else
        echo -e "${RED}❌ kanban-mcp is not running (process not found)${NC}"
        rm -f "$PID_FILE"
    fi
}

show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}⚠️  No log file found${NC}"
        return
    fi
    
    echo -e "${BLUE}📜 kanban-mcp Logs (Press Ctrl+C to stop)${NC}"
    echo "========================================"
    tail -f "$LOG_FILE"
}

# Main script
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        server_status
        ;;
    restart)
        stop_server
        sleep 1
        start_server
        ;;
    logs)
        show_logs
        ;;
    *)
        echo -e "${BLUE}Kanban MCP Server Manager${NC}"
        echo ""
        echo "Usage: $0 {start|stop|status|restart|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the kanban-mcp server"
        echo "  stop     - Stop the kanban-mcp server"
        echo "  status   - Check server status"
        echo "  restart  - Restart the server"
        echo "  logs     - Show server logs (live)"
        exit 1
        ;;
esac