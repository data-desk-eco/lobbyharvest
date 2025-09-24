#!/bin/bash
# Monitor scraper fix sessions

echo "=== Monitoring Scraper Fix Sessions ==="
echo "Time: $(date '+%H:%M:%S')"
echo ""

sessions=("fix-fara" "fix-australian" "fix-french" "fix-austrian" "fix-italian")
names=("FARA" "Australian" "French HATVP" "Austrian" "Italian")

for i in "${!sessions[@]}"; do
    session="${sessions[$i]}"
    name="${names[$i]}"

    echo "[$name Fix]"
    if tmux has-session -t $session 2>/dev/null; then
        # Get last meaningful output
        output=$(tmux capture-pane -t $session -p | tail -30 | grep -E "Fixed|Testing|Success|Error|Writing|Found|✓|✗|Failed|Working" | tail -3)
        if [ -z "$output" ]; then
            # Check if actively working
            recent=$(tmux capture-pane -t $session -p | tail -5 | grep -v "^$" | tail -1)
            if [ -n "$recent" ]; then
                echo "  ⏳ Working..."
            else
                echo "  ⏳ Starting..."
            fi
        else
            echo "$output" | sed 's/^/  /'
        fi
    else
        echo "  ❌ Session not found"
    fi
    echo ""
done

echo "=== File Changes ==="
for dir in ../lobbyharvest-fix-*; do
    if [ -d "$dir" ]; then
        name=$(basename $dir | sed 's/lobbyharvest-fix-//')
        # Check for modified files
        cd "$dir" 2>/dev/null
        if git diff --name-only 2>/dev/null | grep -q ".py"; then
            echo "✓ $name: Files modified"
            git diff --stat 2>/dev/null | grep ".py" | sed 's/^/  /'
        else
            echo "⏳ $name: No changes yet"
        fi
        cd - > /dev/null 2>&1
    fi
done