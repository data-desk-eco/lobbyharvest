#!/bin/bash
# Monitor all tmux agent sessions

echo "=== Monitoring Claude Agent Sessions ==="
echo ""

for session in austrian cyprus italian au-foreign; do
    echo "[$session]"
    if tmux has-session -t $session 2>/dev/null; then
        output=$(tmux capture-pane -t $session -p | tail -10 | grep -E "Created|Error|Writing|Testing|Found|✓|✗|Failed" | tail -5)
        if [ -z "$output" ]; then
            echo "  Working..."
        else
            echo "$output" | sed 's/^/  /'
        fi
    else
        echo "  Session not found"
    fi
    echo ""
done

echo "=== File Status ==="
for dir in ../lobbyharvest-*; do
    if [ -d "$dir" ]; then
        branch=$(basename $dir | sed 's/lobbyharvest-//')
        if [ -f "$dir/lobbyharvest/src/scrapers/${branch}_lobbying.py" ] || [ -f "$dir/lobbyharvest/src/scrapers/${branch//-/_}_lobbying.py" ] || [ -f "$dir/lobbyharvest/src/scrapers/au_foreign_influence.py" ]; then
            echo "✓ $branch: scraper created"
        else
            echo "⏳ $branch: in progress"
        fi
    fi
done