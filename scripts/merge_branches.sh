#!/bin/bash
# Merge completed scraper branches into main

set -e

BRANCHES=("feature/lobbyfacts" "feature/uk-lobbying" "feature/australia" "feature/fara" "feature/irish" "feature/opensecrets")
MAIN_DIR="/home/louis/Projects/lobbyharvest"

cd "$MAIN_DIR"

echo "Checking for completed scrapers..."

for branch in "${BRANCHES[@]}"; do
    # Check if branch has commits beyond main
    commits=$(git rev-list --count main.."$branch" 2>/dev/null || echo 0)

    if [ "$commits" -gt 0 ]; then
        echo ""
        echo "Branch $branch has $commits new commit(s)"
        git log --oneline main.."$branch"

        read -p "Merge $branch into main? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git checkout main
            git merge --no-ff "$branch" -m "Merge $branch: Add scraper module"
            echo "✓ Merged $branch"
        fi
    else
        echo "⏭ Skipping $branch (no new commits)"
    fi
done

echo ""
echo "Final status:"
git log --oneline -5