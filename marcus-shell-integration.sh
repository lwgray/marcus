#!/bin/bash
# Marcus Shell Integration
# Add this to your ~/.bashrc or ~/.zshrc for easy Marcus management

# Marcus management function
marcus() {
    local MARCUS_DIR="$HOME/dev/marcus"  # Update this path to your Marcus directory
    
    if [ ! -d "$MARCUS_DIR" ]; then
        echo "❌ Marcus directory not found at $MARCUS_DIR"
        echo "   Please update MARCUS_DIR in your shell profile"
        return 1
    fi
    
    cd "$MARCUS_DIR" && ./marcus "$@"
}

# Aliases for common operations
alias marcus-stop="marcus stop"
alias marcus-restart="marcus restart"
alias marcus-status="marcus status"
alias marcus-logs="tail -f ~/dev/marcus/logs/conversations/realtime_*.jsonl"

# Add to your shell profile with:
# echo "source ~/dev/marcus/marcus-shell-integration.sh" >> ~/.bashrc
# or
# echo "source ~/dev/marcus/marcus-shell-integration.sh" >> ~/.zshrc