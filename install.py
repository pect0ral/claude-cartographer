#!/usr/bin/env python3
"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Unified installer script.

Usage:
    python install.py [project_path]        # Install (default: current directory)
    python install.py --update              # Update existing installation
    python install.py --uninstall           # Remove installation
    python install.py --force               # Force fresh install
"""

import os
import sys
from pathlib import Path


def main():
    """Main installer entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Codebase Cartographer - Token-optimized codebase mapping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Fresh install in current directory
    python install.py

    # Install in specific project
    python install.py /path/to/project

    # Update existing installation (preserves config and database)
    python install.py --update
    python install.py -u /path/to/project

    # Force fresh install (removes existing)
    python install.py --force
    python install.py -f /path/to/project

    # Uninstall
    python install.py --uninstall
    python install.py --uninstall --keep-db  # Backup database

Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
"""
    )

    parser.add_argument(
        'project_root',
        nargs='?',
        default=os.getcwd(),
        help='Project root directory (default: current directory)'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--update', '-u',
        action='store_true',
        help='Update existing installation, preserving user configuration'
    )
    group.add_argument(
        '--uninstall', '--remove',
        action='store_true',
        help='Remove cartographer from the project'
    )
    group.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force fresh installation (removes existing)'
    )

    parser.add_argument(
        '--keep-db',
        action='store_true',
        help='With --uninstall: backup the codebase database'
    )

    args = parser.parse_args()

    project_path = Path(args.project_root).resolve()

    # Check if we're in the source directory
    src_dir = Path(__file__).parent / 'src' / 'cartographer'

    if not src_dir.exists():
        print(f"\nError: Source directory not found at {src_dir}")
        print("Please run this script from the repository root.")
        sys.exit(1)

    # Add source to path
    sys.path.insert(0, str(Path(__file__).parent / 'src'))

    try:
        from cartographer.bootstrap import CartographerInstaller

        installer = CartographerInstaller(
            project_root=project_path,
            source_dir=src_dir
        )

        if args.uninstall:
            success = installer.uninstall(keep_db=args.keep_db)
        elif args.update:
            success = installer.update()
        else:
            success = installer.install(force=args.force)

        sys.exit(0 if success else 1)

    except ImportError as e:
        print(f"\nError importing module: {e}")
        print("Please ensure all source files are present.")
        sys.exit(1)


if __name__ == '__main__':
    main()
