#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

# Normalize TERM for non-interactive shells (IDE terminals, CI, cron)
if [ "$TERM" = "dumb" ] || [ -z "$TERM" ]; then
    export TERM=xterm-256color
fi

cd /Users/lwgray/dev/marcus/implementation || exit 1
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Configuring Marcus MCP..."
claude mcp add marcus -t http http://localhost:4298/mcp 2>/dev/null || true
echo ""
echo "Creating Marcus project: pomodoro_timer"
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir /Users/lwgray/dev/marcus/implementation   --dangerously-skip-permissions --print < /Users/lwgray/dev/marcus/prompts/project_creator.txt
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
