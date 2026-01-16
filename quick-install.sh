#!/bin/bash
# Codebase Cartographer - Quick Installation
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
#
# Passes all arguments to the Python installer.
#
# Usage:
#   ./quick-install.sh                         # Install in current directory
#   ./quick-install.sh /path/to/project        # Install in specific directory
#   ./quick-install.sh --update                # Update existing installation
#   ./quick-install.sh --uninstall             # Remove installation
#   ./quick-install.sh --force                 # Force fresh install
#   ./quick-install.sh --help                  # Show all options

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python not found. Please install Python 3.8+."
    exit 1
fi

# Pass all arguments to the installer
exec "$PYTHON" "$SCRIPT_DIR/install.py" "$@"
