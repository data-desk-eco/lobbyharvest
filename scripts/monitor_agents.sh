#!/bin/bash
# Monitor all scraper agents progress

sessions=("lobbyfacts" "uk-lobbying" "australia" "fara" "irish" "opensecrets")

for session in "${sessions[@]}"; do
    echo "========================================="
    echo "SESSION: $session"
    echo "========================================="

    # Check if session exists
    if tmux has-session -t "$session" 2>/dev/null; then
        # Get last 10 lines of activity
        echo "Recent activity:"
        tmux capture-pane -t "$session" -p | tail -10 | grep -E "(✓|●|✽|Writing|Creating|Committing|Error)" || echo "No recent activity markers"

        # Check git status in worktree
        worktree="/tmp/lobbyharvest-worktrees/${session//-/_}"
        if [ -d "$worktree" ]; then
            echo ""
            echo "Git status:"
            cd "$worktree" && git status --short
        fi
    else
        echo "Session not found"
    fi
    echo ""
done