"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Unified installer with install, update, and uninstall support.
"""

import os
import sys
import subprocess
import shutil
import json
import venv
import re
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime


# Markers for identifying cartographer sections in files
CARTOGRAPHER_START_MARKER = "<!-- CARTOGRAPHER_START -->"
CARTOGRAPHER_END_MARKER = "<!-- CARTOGRAPHER_END -->"


class CartographerInstaller:
    """
    Unified installer for Codebase Cartographer.

    Supports:
    - install: Fresh installation
    - update: Update existing installation, preserving user config
    - uninstall: Clean removal of all cartographer components

    Usage:
        installer = CartographerInstaller('/path/to/project')
        installer.install()      # Fresh install
        installer.update()       # Update preserving config
        installer.uninstall()    # Clean removal
    """

    VERSION = "3.1.0"

    CORE_DEPENDENCIES = [
        'click>=8.0.0',
        'watchdog>=2.1.0',
        'tiktoken>=0.5.0',
    ]

    OPTIONAL_DEPENDENCIES = [
        'tree-sitter>=0.21.0',
    ]

    def __init__(self, project_root: Path, source_dir: Optional[Path] = None):
        self.project_root = Path(project_root).resolve()
        self.claude_map_dir = self.project_root / '.claude-map'
        self.claude_dir = self.project_root / '.claude'
        self.venv_dir = self.claude_map_dir / 'venv'
        self.bin_dir = self.claude_map_dir / 'bin'
        self.src_dir = self.claude_map_dir / 'src'
        self.cache_dir = self.claude_map_dir / 'cache'
        self.logs_dir = self.claude_map_dir / 'logs'

        # Source directory (where the cartographer source code is)
        if source_dir:
            self.source_dir = Path(source_dir).resolve()
        else:
            self.source_dir = Path(__file__).parent

        # Python paths
        self.system_python = sys.executable
        if sys.platform == 'win32':
            self.venv_python = self.venv_dir / 'Scripts' / 'python.exe'
            self.venv_pip = self.venv_dir / 'Scripts' / 'pip.exe'
        else:
            self.venv_python = self.venv_dir / 'bin' / 'python'
            self.venv_pip = self.venv_dir / 'bin' / 'pip'

        # Absolute path to claude-map binary (for embedding in generated files)
        self.claude_map_bin = str(self.claude_map_dir / 'bin' / 'claude-map')

    def is_installed(self) -> bool:
        """Check if cartographer is already installed."""
        return self.venv_python.exists() and (self.claude_map_dir / 'config.json').exists()

    def get_installed_version(self) -> Optional[str]:
        """Get the currently installed version."""
        config_file = self.claude_map_dir / 'config.json'
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                return config.get('version')
            except:
                pass
        return None

    # =========================================================================
    # INSTALL
    # =========================================================================

    def install(self, force: bool = False) -> bool:
        """
        Fresh installation of Codebase Cartographer.

        Args:
            force: If True, remove existing installation first

        Returns:
            True if successful
        """
        self._print_header("Installation")

        if self.is_installed():
            if force:
                print("Existing installation found. Removing for fresh install...")
                self._remove_claude_map_dir()
            else:
                print("Cartographer is already installed.")
                print("Use --update to update, or --force to reinstall.")
                return False

        try:
            self._create_directories()
            self._create_virtualenv()
            self._upgrade_pip()
            self._install_dependencies()
            self._copy_source()
            self._create_launchers()
            self._create_config()

            if not self._verify_installation():
                print("\nInstallation verification failed!")
                return False

            self._install_claude_integration()
            self._print_success("Installation")
            return True

        except Exception as e:
            print(f"\nInstallation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    # =========================================================================
    # UPDATE
    # =========================================================================

    def update(self) -> bool:
        """
        Update existing installation, preserving user configuration.

        - Updates source code and dependencies
        - Preserves codebase.db (the map)
        - Preserves user's CLAUDE.md content (only updates cartographer section)
        - Preserves user's .claude/settings.json (only updates cartographer entries)

        Returns:
            True if successful
        """
        self._print_header("Update")

        if not self.is_installed():
            print("Cartographer is not installed. Running fresh install...")
            return self.install()

        old_version = self.get_installed_version()
        print(f"Current version: {old_version or 'unknown'}")
        print(f"New version: {self.VERSION}")

        try:
            # Backup important files
            backup = self._backup_user_data()

            # Update components (preserving venv if possible)
            print("\nUpdating source code...")
            self._copy_source()

            print("Updating launchers...")
            self._create_launchers()

            print("Updating configuration...")
            self._update_config()

            # Update Claude integration (preserving user content)
            print("Updating Claude integration...")
            self._update_claude_integration()

            # Restore any backup data if needed
            self._restore_user_data(backup)

            if not self._verify_installation():
                print("\nUpdate verification failed!")
                return False

            self._print_success("Update")
            return True

        except Exception as e:
            print(f"\nUpdate failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _backup_user_data(self) -> dict:
        """Backup user data that should be preserved during update."""
        backup = {}

        # Backup codebase.db path (don't copy, just note it exists)
        db_path = self.claude_map_dir / 'codebase.db'
        backup['has_db'] = db_path.exists()

        return backup

    def _restore_user_data(self, backup: dict):
        """Restore user data after update."""
        # Currently just a placeholder - the db is preserved in place
        pass

    def _update_config(self):
        """Update config file, preserving user settings."""
        config_file = self.claude_map_dir / 'config.json'

        # Load existing config
        existing = {}
        if config_file.exists():
            try:
                existing = json.loads(config_file.read_text())
            except:
                pass

        # Update version and installation info
        existing['version'] = self.VERSION
        existing.setdefault('installation', {})
        existing['installation']['type'] = 'portable'
        existing['installation']['project_root'] = str(self.project_root)
        existing['installation']['claude_dir'] = str(self.claude_map_dir)
        existing['installation']['updated_at'] = datetime.now().isoformat()

        # Preserve user settings, add defaults for new ones
        existing.setdefault('settings', {})
        existing['settings'].setdefault('max_workers', os.cpu_count() or 4)
        existing['settings'].setdefault('cache_enabled', True)
        existing['settings'].setdefault('watch_enabled', True)
        existing['settings'].setdefault('max_cache_size_mb', 128)
        existing['settings'].setdefault('ignore_patterns', [
            'node_modules', '.git', '__pycache__', 'venv', '.venv',
            'dist', 'build', '.next', 'coverage', '.pytest_cache',
        ])

        config_file.write_text(json.dumps(existing, indent=2))

    # =========================================================================
    # UNINSTALL
    # =========================================================================

    def uninstall(self, keep_db: bool = False) -> bool:
        """
        Safely remove Codebase Cartographer.

        Args:
            keep_db: If True, preserve codebase.db for potential reinstall

        Removes:
        - .claude-map/ directory (optionally preserving codebase.db)
        - Cartographer hooks from .claude/hooks/
        - Cartographer skill from .claude/skills/
        - Cartographer command from .claude/commands/
        - Cartographer section from CLAUDE.md
        - Cartographer entries from .claude/settings.json

        Returns:
            True if successful
        """
        self._print_header("Uninstall")

        if not self.claude_map_dir.exists() and not self._has_claude_integration():
            print("Cartographer does not appear to be installed.")
            return True

        try:
            # Remove Claude integration first
            print("Removing Claude integration...")
            self._remove_claude_integration()

            # Remove .claude-map directory
            if self.claude_map_dir.exists():
                if keep_db:
                    db_path = self.claude_map_dir / 'codebase.db'
                    if db_path.exists():
                        backup_path = self.project_root / '.cartographer-backup-codebase.db'
                        shutil.copy2(db_path, backup_path)
                        print(f"  Backed up database to {backup_path}")

                print(f"Removing {self.claude_map_dir}...")
                shutil.rmtree(self.claude_map_dir)

            print("\n" + "=" * 70)
            print("Uninstall Complete!")
            print("=" * 70)
            if keep_db:
                print(f"\nDatabase backed up to: .cartographer-backup-codebase.db")
                print("To restore after reinstall, move it to .claude-map/codebase.db")
            print("\nCartographer has been removed from this project.")
            return True

        except Exception as e:
            print(f"\nUninstall failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _has_claude_integration(self) -> bool:
        """Check if any Claude integration files exist."""
        checks = [
            self.claude_dir / 'hooks' / 'cartographer-update.sh',
            self.claude_dir / 'skills' / 'cartographer.md',
            self.claude_dir / 'commands' / 'map.md',
        ]
        return any(p.exists() for p in checks)

    def _remove_claude_integration(self):
        """Remove all Claude integration components."""
        # Remove hooks
        hooks_dir = self.claude_dir / 'hooks'
        for hook in ['cartographer-update.sh', 'cartographer-finalize.sh',
                     'cartographer-update.bat', 'cartographer-finalize.bat']:
            hook_path = hooks_dir / hook
            if hook_path.exists():
                hook_path.unlink()
                print(f"  Removed hook: {hook}")

        # Remove skill
        skill_path = self.claude_dir / 'skills' / 'cartographer.md'
        if skill_path.exists():
            skill_path.unlink()
            print("  Removed skill: cartographer.md")

        # Remove command
        cmd_path = self.claude_dir / 'commands' / 'map.md'
        if cmd_path.exists():
            cmd_path.unlink()
            print("  Removed command: map.md")

        # Clean up settings.json
        self._clean_settings_json()

        # Remove cartographer section from CLAUDE.md
        self._remove_from_claude_md()

    def _clean_settings_json(self):
        """Remove cartographer entries from settings.json."""
        settings_path = self.claude_dir / 'settings.json'
        if not settings_path.exists():
            return

        try:
            settings = json.loads(settings_path.read_text())
            modified = False

            # Remove cartographer hooks
            if 'hooks' in settings:
                for hook_type in ['PostToolUse', 'Stop']:
                    if hook_type in settings['hooks']:
                        original_len = len(settings['hooks'][hook_type])
                        settings['hooks'][hook_type] = [
                            h for h in settings['hooks'][hook_type]
                            if not self._is_cartographer_hook(h)
                        ]
                        if len(settings['hooks'][hook_type]) < original_len:
                            modified = True
                        # Remove empty arrays
                        if not settings['hooks'][hook_type]:
                            del settings['hooks'][hook_type]

                # Remove empty hooks object
                if not settings['hooks']:
                    del settings['hooks']

            # Remove cartographer permissions
            if 'permissions' in settings and 'allow' in settings['permissions']:
                original_len = len(settings['permissions']['allow'])
                settings['permissions']['allow'] = [
                    p for p in settings['permissions']['allow']
                    if 'claude-map' not in p
                ]
                if len(settings['permissions']['allow']) < original_len:
                    modified = True

            if modified:
                settings_path.write_text(json.dumps(settings, indent=2))
                print("  Cleaned settings.json")

        except Exception as e:
            print(f"  Warning: Could not clean settings.json: {e}")

    def _is_cartographer_hook(self, hook_entry: dict) -> bool:
        """Check if a hook entry belongs to cartographer."""
        if not isinstance(hook_entry, dict):
            return False
        hooks = hook_entry.get('hooks', [])
        for h in hooks:
            if isinstance(h, dict):
                cmd = h.get('command', '')
                if 'cartographer' in cmd:
                    return True
        return False

    def _remove_from_claude_md(self):
        """Remove cartographer section from CLAUDE.md."""
        claude_md = self.project_root / 'CLAUDE.md'
        if not claude_md.exists():
            return

        content = claude_md.read_text()

        # Try to remove marked section first
        if CARTOGRAPHER_START_MARKER in content:
            pattern = re.compile(
                re.escape(CARTOGRAPHER_START_MARKER) + r'.*?' + re.escape(CARTOGRAPHER_END_MARKER),
                re.DOTALL
            )
            new_content = pattern.sub('', content)
            # Clean up extra blank lines
            new_content = re.sub(r'\n{3,}', '\n\n', new_content)
            claude_md.write_text(new_content.strip() + '\n')
            print("  Removed cartographer section from CLAUDE.md")
            return

        # Fallback: try to find and remove the section by content
        if 'Codebase Cartographer' in content:
            # Find the section start
            lines = content.split('\n')
            start_idx = None
            end_idx = None

            for i, line in enumerate(lines):
                if '## CRITICAL: Use Codebase Cartographer First' in line or \
                   '## CRITICAL: Use Codebase Cartographer' in line:
                    start_idx = i
                elif start_idx is not None and line.startswith('## ') and i > start_idx:
                    end_idx = i
                    break

            if start_idx is not None:
                if end_idx is None:
                    end_idx = len(lines)
                # Remove the section
                new_lines = lines[:start_idx] + lines[end_idx:]
                new_content = '\n'.join(new_lines)
                # Clean up extra blank lines
                new_content = re.sub(r'\n{3,}', '\n\n', new_content)
                claude_md.write_text(new_content.strip() + '\n')
                print("  Removed cartographer section from CLAUDE.md")

    # =========================================================================
    # CLAUDE INTEGRATION
    # =========================================================================

    def _install_claude_integration(self):
        """Install Claude Code integration (hooks, skills, commands, CLAUDE.md)."""
        print("\nInstalling Claude Code integration...")

        self._ensure_claude_directories()
        self._create_hooks()
        self._create_skill()
        self._create_command()
        self._update_settings_json()
        self._update_claude_md()

        print("  Claude integration installed")

    def _update_claude_integration(self):
        """Update Claude integration, preserving user content."""
        self._ensure_claude_directories()
        self._create_hooks()  # Hooks are regenerated (they use absolute paths)
        self._create_skill()  # Skill is regenerated
        self._create_command()  # Command is regenerated
        self._update_settings_json()  # Settings are merged
        self._update_claude_md()  # CLAUDE.md section is replaced, user content preserved

    def _ensure_claude_directories(self):
        """Create .claude directories if they don't exist."""
        for d in [self.claude_dir, self.claude_dir / 'hooks',
                  self.claude_dir / 'skills', self.claude_dir / 'commands']:
            d.mkdir(parents=True, exist_ok=True)

    def _create_hooks(self):
        """Create hook scripts with absolute paths."""
        base_dir = str(self.project_root)
        claude_map_dir = str(self.claude_map_dir)
        hooks_dir = self.claude_dir / 'hooks'

        # Post-tool-use hook
        update_hook = f'''#!/bin/bash
# Codebase Cartographer - Auto-update hook
# Copyright (c) 2025 Breach Craft

BASE_DIR="{base_dir}"
CLAUDE_MAP_DIR="{claude_map_dir}"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\\([^"]*\\)"$/\\1/')

case "$TOOL" in
    Edit|Write|NotebookEdit)
        FILE=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\\([^"]*\\)"$/\\1/')
        if [ -n "$FILE" ] && [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ]; then
            mkdir -p "${{CLAUDE_MAP_DIR}}/cache"
            echo "$FILE" >> "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null || true
        fi
        ;;
esac
exit 0
'''
        update_path = hooks_dir / 'cartographer-update.sh'
        update_path.write_text(update_hook)
        update_path.chmod(0o755)

        # Session end hook
        finalize_hook = f'''#!/bin/bash
# Codebase Cartographer - Session end hook
# Copyright (c) 2025 Breach Craft

CLAUDE_MAP_DIR="{claude_map_dir}"
CLAUDE_MAP="${{CLAUDE_MAP_DIR}}/bin/claude-map"

if [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ] && [ -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" ]; then
    "$CLAUDE_MAP" update 2>/dev/null || true
    rm -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null || true
fi
exit 0
'''
        finalize_path = hooks_dir / 'cartographer-finalize.sh'
        finalize_path.write_text(finalize_hook)
        finalize_path.chmod(0o755)

    def _create_skill(self):
        """Create the cartographer skill file."""
        skill_content = f'''# Codebase Cartographer Skill

Use `{self.claude_map_bin}` for token-efficient code exploration.

## Commands
```bash
{self.claude_map_bin} find <name>      # Find component by name
{self.claude_map_bin} query "<text>"   # Natural language query
{self.claude_map_bin} show <file>      # Show file components
{self.claude_map_bin} exports          # List public API
{self.claude_map_bin} update           # Update map
```

## Best Practice
Search with cartographer BEFORE reading files to save 95%+ tokens.
'''
        skill_path = self.claude_dir / 'skills' / 'cartographer.md'
        skill_path.write_text(skill_content)

    def _create_command(self):
        """Create the /map command definition."""
        cmd_content = f'''# /map - Codebase Cartographer

Manage the codebase map for token-efficient exploration.

## Usage
- `/map` or `/map update` - Update the map
- `/map init` - Initialize mapping (first time)
- `/map stats` - Show statistics
- `/map find <name>` - Quick search

## Execution
Run: `{self.claude_map_bin} <subcommand>`
'''
        cmd_path = self.claude_dir / 'commands' / 'map.md'
        cmd_path.write_text(cmd_content)

    def _update_settings_json(self):
        """Update .claude/settings.json with hook configuration."""
        settings_path = self.claude_dir / 'settings.json'
        update_hook_cmd = str(self.claude_dir / 'hooks' / 'cartographer-update.sh')
        finalize_hook_cmd = str(self.claude_dir / 'hooks' / 'cartographer-finalize.sh')

        # Load existing settings
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except:
                pass

        # First, remove any existing cartographer hooks
        if 'hooks' in settings:
            for hook_type in ['PostToolUse', 'Stop']:
                if hook_type in settings['hooks']:
                    settings['hooks'][hook_type] = [
                        h for h in settings['hooks'][hook_type]
                        if not self._is_cartographer_hook(h)
                    ]

        # Add hooks
        settings.setdefault('hooks', {})

        # PostToolUse hook
        settings['hooks'].setdefault('PostToolUse', [])
        settings['hooks']['PostToolUse'].append({
            "matcher": "Edit|Write|NotebookEdit",
            "hooks": [{"type": "command", "command": update_hook_cmd}]
        })

        # Stop hook
        settings['hooks'].setdefault('Stop', [])
        settings['hooks']['Stop'].append({
            "matcher": "",
            "hooks": [{"type": "command", "command": finalize_hook_cmd}]
        })

        # Add permissions (remove old, add new)
        settings.setdefault('permissions', {})
        settings['permissions'].setdefault('allow', [])

        # Remove old cartographer permissions
        settings['permissions']['allow'] = [
            p for p in settings['permissions']['allow']
            if 'claude-map' not in p
        ]

        # Add new permission with absolute path
        perm = f"Bash({self.claude_map_bin}:*)"
        if perm not in settings['permissions']['allow']:
            settings['permissions']['allow'].append(perm)

        settings_path.write_text(json.dumps(settings, indent=2))

    def _update_claude_md(self):
        """Update CLAUDE.md, preserving user content."""
        claude_md = self.project_root / 'CLAUDE.md'

        # Generate the cartographer section with markers
        cartographer_section = f'''{CARTOGRAPHER_START_MARKER}
## CRITICAL: Use Codebase Cartographer First

**BEFORE using Read, Grep, or Glob tools to explore code, use the cartographer:**

```bash
{self.claude_map_bin} find <name>      # Find function/class/component by name
{self.claude_map_bin} query "<text>"   # Natural language search
{self.claude_map_bin} show <file>      # Show file structure without reading full content
```

**Why this matters:**
- Saves 95%+ tokens compared to reading full files
- Returns precise line numbers and signatures
- Use Read tool ONLY after cartographer identifies the specific lines you need

**Workflow:**
1. `{self.claude_map_bin} find ComponentName` - get file path and line numbers
2. `Read` tool with specific line range if you need implementation details

**Fallback:** If cartographer returns no results, use native Grep/Glob/Read tools.
{CARTOGRAPHER_END_MARKER}'''

        if claude_md.exists():
            content = claude_md.read_text()

            # If marked section exists, replace it
            if CARTOGRAPHER_START_MARKER in content:
                pattern = re.compile(
                    re.escape(CARTOGRAPHER_START_MARKER) + r'.*?' + re.escape(CARTOGRAPHER_END_MARKER),
                    re.DOTALL
                )
                new_content = pattern.sub(cartographer_section, content)
                claude_md.write_text(new_content)
                return

            # If old-style section exists (no markers), replace it
            if 'Codebase Cartographer' in content:
                self._remove_from_claude_md()
                content = claude_md.read_text()

            # Insert after the first header
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('# '):
                    insert_idx = i + 1
                    while insert_idx < len(lines) and lines[insert_idx].strip() == '':
                        insert_idx += 1
                    break

            lines.insert(insert_idx, '\n' + cartographer_section + '\n')
            claude_md.write_text('\n'.join(lines))
        else:
            # Create new CLAUDE.md
            claude_md.write_text(f"# Project Instructions\n\n{cartographer_section}\n")

    # =========================================================================
    # CORE INSTALLATION METHODS
    # =========================================================================

    def _print_header(self, action: str):
        """Print installation header."""
        print("=" * 70)
        print(f"Codebase Cartographer - {action}")
        print("Copyright (c) 2025 Breach Craft - Mike Piekarski")
        print("=" * 70)
        print(f"\nProject: {self.project_root}")
        print(f"Version: {self.VERSION}")
        print()

    def _print_success(self, action: str):
        """Print success message."""
        print("\n" + "=" * 70)
        print(f"{action} Complete!")
        print("=" * 70)
        print(f"\nInstallation: {self.claude_map_dir}")
        print(f"\nUsage:")
        print(f"  {self.claude_map_bin} init      # Initialize codebase map")
        print(f"  {self.claude_map_bin} find X    # Find component")
        print(f"  {self.claude_map_bin} query X   # Natural language query")
        print(f"  {self.claude_map_bin} stats     # Show statistics")

    def _remove_claude_map_dir(self):
        """Remove the .claude-map directory."""
        if self.claude_map_dir.exists():
            shutil.rmtree(self.claude_map_dir)

    def _create_directories(self):
        """Create directory structure."""
        print("Creating directories...")
        for d in [self.claude_map_dir, self.venv_dir, self.bin_dir,
                  self.src_dir, self.cache_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _create_virtualenv(self):
        """Create virtual environment."""
        print("Creating virtual environment...")
        if self.venv_python.exists():
            return
        builder = venv.EnvBuilder(with_pip=True, clear=True)
        builder.create(self.venv_dir)

    def _upgrade_pip(self):
        """Upgrade pip in virtual environment."""
        print("Upgrading pip...")
        self._run_pip(['install', '--upgrade', 'pip', 'setuptools', 'wheel'])

    def _install_dependencies(self):
        """Install dependencies."""
        print("Installing dependencies...")

        for dep in self.CORE_DEPENDENCIES:
            try:
                self._run_pip(['install', dep])
                print(f"  + {dep}")
            except Exception as e:
                print(f"  ! Failed: {dep} - {e}")
                raise

        for dep in self.OPTIONAL_DEPENDENCIES:
            try:
                self._run_pip(['install', dep])
                print(f"  + {dep}")
            except:
                print(f"  - Skipped: {dep} (optional)")

    def _run_pip(self, args: List[str]):
        """Run pip command."""
        cmd = [str(self.venv_python), '-m', 'pip'] + args + ['--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.claude_map_dir))
        if result.returncode != 0:
            raise Exception(f"pip failed: {result.stderr}")

    def _copy_source(self):
        """Copy source code."""
        print("Copying source code...")
        target = self.src_dir / 'cartographer'
        target.mkdir(parents=True, exist_ok=True)

        source_files = [
            '__init__.py', '__main__.py', 'database.py', 'mapper.py',
            'parsers.py', 'integration.py', 'watcher.py', 'benchmark.py',
            'cli.py', 'bootstrap.py', 'claude_integration.py', 'session_tracker.py',
        ]

        for filename in source_files:
            src = self.source_dir / filename
            if src.exists():
                shutil.copy2(src, target / filename)

    def _create_launchers(self):
        """Create launcher scripts."""
        print("Creating launchers...")
        if sys.platform == 'win32':
            self._create_windows_launcher()
        else:
            self._create_unix_launcher()

    def _create_unix_launcher(self):
        """Create Unix launcher."""
        launcher = self.bin_dir / 'claude-map'
        content = f'''#!/bin/bash
# Codebase Cartographer
# Copyright (c) 2025 Breach Craft

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$CLAUDE_DIR/venv/bin/python"
SRC_DIR="$CLAUDE_DIR/src"

export PYTHONPATH="$SRC_DIR:$PYTHONPATH"
exec "$VENV_PYTHON" -m cartographer.cli "$@"
'''
        launcher.write_text(content)
        launcher.chmod(0o755)

    def _create_windows_launcher(self):
        """Create Windows launcher."""
        launcher = self.bin_dir / 'claude-map.bat'
        content = f'''@echo off
REM Codebase Cartographer
REM Copyright (c) 2025 Breach Craft

set SCRIPT_DIR=%~dp0
set CLAUDE_DIR=%SCRIPT_DIR%..
set VENV_PYTHON=%CLAUDE_DIR%\\venv\\Scripts\\python.exe
set SRC_DIR=%CLAUDE_DIR%\\src

set PYTHONPATH=%SRC_DIR%;%PYTHONPATH%
"%VENV_PYTHON%" -m cartographer.cli %*
'''
        launcher.write_text(content)

    def _create_config(self):
        """Create configuration file."""
        print("Creating configuration...")
        config = {
            'version': self.VERSION,
            'installation': {
                'type': 'portable',
                'project_root': str(self.project_root),
                'claude_dir': str(self.claude_map_dir),
                'installed_at': datetime.now().isoformat(),
            },
            'settings': {
                'max_workers': os.cpu_count() or 4,
                'cache_enabled': True,
                'watch_enabled': True,
                'max_cache_size_mb': 128,
                'ignore_patterns': [
                    'node_modules', '.git', '__pycache__', 'venv', '.venv',
                    'dist', 'build', '.next', 'coverage', '.pytest_cache',
                ],
            },
            'attribution': {
                'author': 'Mike Piekarski',
                'email': 'mp@breachcraft.io',
                'company': 'Breach Craft',
                'copyright': 'Copyright (c) 2025 Breach Craft',
            }
        }
        config_file = self.claude_map_dir / 'config.json'
        config_file.write_text(json.dumps(config, indent=2))

    def _verify_installation(self) -> bool:
        """Verify installation."""
        print("Verifying installation...")

        if not self.venv_python.exists():
            print("  Error: Python not found")
            return False

        cmd = [
            str(self.venv_python), '-c',
            'import sys; sys.path.insert(0, "src"); from cartographer import __version__; print(__version__)'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.claude_map_dir))

        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
            return False

        print(f"  Version: {result.stdout.strip()}")
        print("  Verification passed!")
        return True


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Codebase Cartographer - Token-optimized codebase mapping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m cartographer.bootstrap                    # Install in current dir
    python -m cartographer.bootstrap /path/to/project   # Install in specific dir
    python -m cartographer.bootstrap --update           # Update existing install
    python -m cartographer.bootstrap --uninstall        # Remove installation
    python -m cartographer.bootstrap --force            # Force fresh install

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

    # Find source directory
    source_dir = Path(__file__).parent
    if not (source_dir / '__init__.py').exists():
        # Running from install.py wrapper
        source_dir = Path(__file__).parent / 'src' / 'cartographer'

    installer = CartographerInstaller(project_path, source_dir)

    if args.uninstall:
        success = installer.uninstall(keep_db=args.keep_db)
    elif args.update:
        success = installer.update()
    else:
        success = installer.install(force=args.force)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
