# Parallel Development with Tmux Sessions

## Overview
This document describes the parallel development approach used to accelerate development of the lobbyharvest project using multiple Claude Code agents orchestrated through tmux sessions.

## Architecture

### Main Orchestrator
The primary Claude session acts as an orchestrator, managing multiple parallel development tasks by:
1. Creating git worktrees for isolated development branches
2. Spawning tmux sessions with Claude Code agents
3. Monitoring progress and merging completed work
4. Coordinating between agents to avoid conflicts

### Parallel Agents
Each tmux session runs an independent Claude Code agent with:
- Isolated git worktree to prevent conflicts
- Specific task assignment (e.g., "develop UK lobbying scraper")
- `--dangerously-skip-permissions` flag for better performance on isolated servers

## Implementation

### 1. Setup Worktrees
```bash
# Create worktrees for parallel development
git worktree add -b feature/lobbyfacts ../lobbyharvest-lobbyfacts
git worktree add -b feature/uk-scraper ../lobbyharvest-uk
git worktree add -b feature/aus-scraper ../lobbyharvest-aus
```

### 2. Launch Agent Sessions
```bash
# Start tmux session with Claude agent
tmux new-session -d -s lobbyfacts -c ../lobbyharvest-lobbyfacts
tmux send-keys -t lobbyfacts "claude --dangerously-skip-permissions" Enter
sleep 2
tmux send-keys -t lobbyfacts "Create a lightweight scraper for lobbyfacts.eu..." Enter
```

### 3. Monitor Progress
```bash
# Check agent output
tmux capture-pane -t lobbyfacts -p | tail -50

# List active sessions
tmux list-sessions
```

### 4. Merge Completed Work
```bash
# After agent completes task
git merge feature/lobbyfacts --no-ff
git worktree remove ../lobbyharvest-lobbyfacts
tmux kill-session -t lobbyfacts
```

## Benefits
- **Parallelization**: Multiple scrapers developed simultaneously
- **Isolation**: Each agent works in separate branch/directory
- **Efficiency**: 3-5x faster development for multi-component projects
- **Coordination**: Main orchestrator ensures consistency

## Limitations
- Server resources limit to ~5 concurrent sessions
- Requires orchestrator to manage merge conflicts
- Agents can't directly communicate with each other

## Best Practices
1. Keep agent tasks focused and well-defined
2. Monitor output regularly to catch issues early
3. Close sessions when complete to free resources
4. Use descriptive session names matching branch names
5. Merge frequently to avoid large conflicts

## Example Session
```bash
# Main orchestrator workflow
tmux new-session -d -s uk-scraper -c ../lobbyharvest-uk
tmux send-keys -t uk-scraper "claude --dangerously-skip-permissions" Enter
sleep 2
tmux send-keys -t uk-scraper "Develop a UK lobbying register scraper using requests and BeautifulSoup. The scraper should be in src/scrapers/uk_lobbying.py with a scrape() function that takes a firm name and returns a list of client dictionaries." Enter

# Check progress periodically
watch -n 10 'tmux capture-pane -t uk-scraper -p | tail -30'

# When complete
git merge feature/uk-scraper
tmux kill-session -t uk-scraper
```

This approach enabled rapid development of multiple scrapers in parallel while maintaining code quality and avoiding conflicts.