#!/bin/bash
# Demo script for PM Agent with Planka recording

echo "PM Agent Demo with Screen Recording"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PM Agent is running
check_pm_agent() {
    echo -e "${BLUE}Checking PM Agent status...${NC}"
    if pgrep -f "pm_agent_mcp_server.py" > /dev/null; then
        echo -e "${GREEN}✓ PM Agent is running${NC}"
        return 0
    else
        echo -e "${YELLOW}✗ PM Agent is not running${NC}"
        return 1
    fi
}

# Start PM Agent if needed
start_pm_agent() {
    echo -e "${BLUE}Starting PM Agent...${NC}"
    cd /Users/lwgray/dev/pm-agent
    python pm_agent_mcp_server.py &
    PM_AGENT_PID=$!
    sleep 5
    echo -e "${GREEN}✓ PM Agent started (PID: $PM_AGENT_PID)${NC}"
}

# Menu for demo options
show_menu() {
    echo ""
    echo "Demo Options:"
    echo "1. Quick Demo (1 worker, 5 minutes)"
    echo "2. Full Demo (3 workers, 15 minutes)" 
    echo "3. Custom Demo"
    echo "4. Exit"
    echo ""
    read -p "Select option: " choice
}

# Run quick demo
run_quick_demo() {
    echo -e "${BLUE}Starting Quick Demo...${NC}"
    
    # Start recording in background
    echo -e "${YELLOW}Starting screen recording...${NC}"
    python scripts/record_planka_demo.py ffmpeg 300 &
    RECORDER_PID=$!
    sleep 5
    
    # Run single worker
    echo -e "${BLUE}Starting Claude Backend Worker...${NC}"
    echo "1" | python scripts/mock_claude_worker.py &
    WORKER_PID=$!
    
    # Wait for demo to complete
    echo -e "${GREEN}Demo running for 5 minutes...${NC}"
    echo "Watch Planka at http://localhost:3333 to see tasks moving!"
    
    # Show progress
    for i in {1..5}; do
        sleep 60
        echo -e "${YELLOW}Progress: $i/5 minutes${NC}"
    done
    
    # Cleanup
    kill $WORKER_PID 2>/dev/null
    kill $RECORDER_PID 2>/dev/null
    
    echo -e "${GREEN}✓ Demo complete! Check recordings/ for video${NC}"
}

# Run full demo  
run_full_demo() {
    echo -e "${BLUE}Starting Full Demo...${NC}"
    
    # Start recording
    echo -e "${YELLOW}Starting screen recording...${NC}"
    python scripts/record_planka_demo.py ffmpeg 900 &
    RECORDER_PID=$!
    sleep 5
    
    # Run all workers
    echo -e "${BLUE}Starting all Claude Workers...${NC}"
    echo "all" | python scripts/mock_claude_worker.py &
    WORKERS_PID=$!
    
    # Wait for demo
    echo -e "${GREEN}Demo running for 15 minutes...${NC}"
    echo "Watch Planka at http://localhost:3333 to see tasks moving!"
    
    # Show progress
    for i in {1..15}; do
        sleep 60
        echo -e "${YELLOW}Progress: $i/15 minutes${NC}"
    done
    
    # Cleanup
    kill $WORKERS_PID 2>/dev/null
    kill $RECORDER_PID 2>/dev/null
    
    echo -e "${GREEN}✓ Demo complete! Check recordings/ for video${NC}"
}

# Custom demo
run_custom_demo() {
    read -p "Number of workers (1-3): " workers
    read -p "Duration in minutes: " duration
    read -p "Record video? (y/n): " record
    
    if [[ $record == "y" ]]; then
        echo -e "${YELLOW}Starting screen recording...${NC}"
        python scripts/record_planka_demo.py ffmpeg $((duration * 60)) &
        RECORDER_PID=$!
        sleep 5
    fi
    
    echo -e "${BLUE}Starting workers...${NC}"
    if [[ $workers == "1" ]]; then
        echo "1" | python scripts/mock_claude_worker.py &
    else
        echo "all" | python scripts/mock_claude_worker.py &
    fi
    WORKERS_PID=$!
    
    echo -e "${GREEN}Demo running for $duration minutes...${NC}"
    sleep $((duration * 60))
    
    # Cleanup
    kill $WORKERS_PID 2>/dev/null
    [[ ! -z $RECORDER_PID ]] && kill $RECORDER_PID 2>/dev/null
    
    echo -e "${GREEN}✓ Demo complete!${NC}"
}

# Main script
main() {
    echo -e "${BLUE}Setting up PM Agent demo environment...${NC}"
    
    # Check dependencies
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${YELLOW}Warning: ffmpeg not found. Install for screen recording:${NC}"
        echo "  macOS: brew install ffmpeg"
        echo "  Linux: sudo apt-get install ffmpeg"
    fi
    
    # Ensure PM Agent is running
    if ! check_pm_agent; then
        start_pm_agent
    fi
    
    # Ensure Planka is accessible
    echo -e "${BLUE}Checking Planka...${NC}"
    if curl -s http://localhost:3333 > /dev/null; then
        echo -e "${GREEN}✓ Planka is accessible${NC}"
    else
        echo -e "${YELLOW}✗ Cannot reach Planka at http://localhost:3333${NC}"
        echo "Please ensure Planka is running"
        exit 1
    fi
    
    # Run demo menu
    while true; do
        show_menu
        case $choice in
            1) run_quick_demo; break;;
            2) run_full_demo; break;;
            3) run_custom_demo; break;;
            4) echo "Exiting..."; exit 0;;
            *) echo "Invalid option";;
        esac
    done
}

# Cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    # Kill any remaining processes
    pkill -f mock_claude_worker.py 2>/dev/null
    pkill -f record_planka_demo.py 2>/dev/null
    [[ ! -z $PM_AGENT_PID ]] && kill $PM_AGENT_PID 2>/dev/null
    echo -e "${GREEN}Done!${NC}"
}

trap cleanup EXIT

# Run main
main