#!/bin/bash
# Codebase Cartographer - Full Setup
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# Complete setup: install + initialize map + run benchmark
#
# Usage:
#   ./setup.sh                    # Setup in current directory
#   ./setup.sh /path/to/project   # Setup in specific directory
#   ./setup.sh --update           # Update and reinitialize

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT=""
UPDATE_MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --update|-u)
            UPDATE_MODE="--update"
            shift
            ;;
        --force|-f)
            UPDATE_MODE="--force"
            shift
            ;;
        --help|-h)
            echo "Codebase Cartographer - Full Setup"
            echo ""
            echo "Usage:"
            echo "  ./setup.sh [options] [project_path]"
            echo ""
            echo "Options:"
            echo "  --update, -u    Update existing installation"
            echo "  --force, -f     Force fresh installation"
            echo "  --help, -h      Show this help"
            echo ""
            echo "This script installs cartographer, initializes the codebase map,"
            echo "and runs a benchmark to show token savings."
            exit 0
            ;;
        *)
            PROJECT_ROOT="$1"
            shift
            ;;
    esac
done

# Default to current directory
if [ -z "$PROJECT_ROOT" ]; then
    PROJECT_ROOT="$(pwd)"
fi
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

echo "======================================================================"
echo "Codebase Cartographer - Full Setup"
echo "Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>"
echo "======================================================================"
echo ""
echo "Project: $PROJECT_ROOT"
echo ""

# Find Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python 3.8+ is required but not found."
    echo "Please install Python from https://python.org"
    exit 1
fi

echo "Python: $PYTHON"
echo ""

# Step 1: Install/Update Cartographer
echo "Step 1: Installing Codebase Cartographer..."
echo "----------------------------------------------------------------------"
$PYTHON "$SCRIPT_DIR/install.py" $UPDATE_MODE "$PROJECT_ROOT"

# Step 2: Initialize the map
echo ""
echo "Step 2: Initializing codebase map..."
echo "----------------------------------------------------------------------"
CLAUDE_MAP="$PROJECT_ROOT/.claude-map/bin/claude-map"

if [ -f "$CLAUDE_MAP" ]; then
    "$CLAUDE_MAP" init
else
    echo "Error: Installation failed - claude-map not found"
    exit 1
fi

# Step 3: Run benchmark
echo ""
echo "Step 3: Running token optimization benchmark..."
echo "----------------------------------------------------------------------"
"$CLAUDE_MAP" benchmark

# Done
echo ""
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo ""
echo "Installation:"
echo "  Map database: $PROJECT_ROOT/.claude-map/codebase.db"
echo "  CLI tool:     $CLAUDE_MAP"
echo "  Claude hooks: $PROJECT_ROOT/.claude/hooks/"
echo ""
echo "Quick Start:"
echo "  $CLAUDE_MAP find <name>      # Find component"
echo "  $CLAUDE_MAP query '<text>'   # Natural language query"
echo "  $CLAUDE_MAP show <file>      # Show file components"
echo "  $CLAUDE_MAP stats            # Show statistics"
echo ""
echo "Management:"
echo "  ./quick-install.sh --update     # Update to latest version"
echo "  ./quick-install.sh --uninstall  # Remove installation"
echo ""
