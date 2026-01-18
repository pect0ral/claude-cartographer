"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Claude Code integration installer.
Sets up hooks, skills, and commands in the project's .claude directory.
"""

import os
import json
import re
from pathlib import Path
from typing import Optional


class ClaudeIntegrationInstaller:
    """
    Install Claude Code integration components.

    Sets up:
    - .claude/skills/cartographer.md - Skill definition
    - .claude/hooks/ - Auto-update hooks
    - .claude/commands/ - Slash commands
    - CLAUDE.md update - Project instructions
    """

    def __init__(self, project_root: Path, source_dir: Optional[Path] = None):
        self.project_root = Path(project_root).resolve()
        self.claude_dir = self.project_root / '.claude'
        self.claude_map_dir = self.project_root / '.claude-map'

        # Source directory for Claude integration files
        if source_dir:
            self.source_dir = Path(source_dir).resolve()
        else:
            # Look for claude/ directory relative to this file
            self.source_dir = Path(__file__).parent.parent.parent / 'claude'

    def install(self) -> bool:
        """Install all Claude integration components."""
        print("\nInstalling Claude Code integration...")

        try:
            # Create directories
            self._create_directories()

            # Install skill
            self._install_skill()

            # Install hooks
            self._install_hooks()

            # Install commands
            self._install_commands()

            # Update or create CLAUDE.md
            self._update_claude_md()

            # Update settings
            self._update_settings()

            print("  Claude integration installed successfully")
            return True

        except Exception as e:
            print(f"  Error installing Claude integration: {e}")
            return False

    def _create_directories(self):
        """Create required directories."""
        directories = [
            self.claude_dir,
            self.claude_dir / 'skills' / 'cartographer',  # Skill subdirectory per Claude spec
            self.claude_dir / 'hooks',
            self.claude_dir / 'commands',
        ]

        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

    def _install_skill(self):
        """Install the cartographer skill from source with absolute paths."""
        # Claude Code expects: .claude/skills/skill-name/SKILL.md
        dst = self.claude_dir / 'skills' / 'cartographer' / 'SKILL.md'

        # Clean up old skill location (was .claude/skills/cartographer.md)
        old_skill = self.claude_dir / 'skills' / 'cartographer.md'
        if old_skill.exists():
            old_skill.unlink()
            print("    - Removed old skill location: cartographer.md")

        # Try to use source skill file, fall back to generated if not found
        source_skill = self.source_dir / 'skills' / 'cartographer.md'
        if source_skill.exists():
            self._install_skill_from_source(source_skill, dst)
        else:
            self._create_minimal_skill(dst)

    def _install_skill_from_source(self, src: Path, dst: Path):
        """Install skill from source file with path substitution."""
        claude_map_bin = str(self.claude_map_dir / 'bin' / 'claude-map')

        content = src.read_text()
        # Substitute placeholder paths with absolute paths
        content = content.replace('.claude-map/bin/claude-map', claude_map_bin)

        dst.write_text(content)
        print("    + Installed skill: cartographer/SKILL.md")

    def _create_minimal_skill(self, dst: Path):
        """Create minimal skill definition (fallback if source not found)."""
        # Use absolute path to avoid issues when Claude changes working directory
        claude_map_bin = str(self.claude_map_dir / 'bin' / 'claude-map')

        content = f'''---
name: cartographer
description: Token-optimized codebase exploration. Use when finding components, checking dependencies, or understanding code structure. Saves 95%+ tokens vs reading files.
---

# Codebase Cartographer

Use `{claude_map_bin}` for token-efficient code exploration.

## Commands
```bash
{claude_map_bin} find <name>      # Find component
{claude_map_bin} query "<text>"   # Pattern-based query
{claude_map_bin} show <file>      # Show file components
{claude_map_bin} exports          # List public API
{claude_map_bin} update           # Update map
```

## Best Practice
Search with cartographer BEFORE reading files to save 95%+ tokens.
'''
        dst.write_text(content)
        print("    + Created skill: cartographer/SKILL.md (minimal)")

    def _install_hooks(self):
        """Install hook scripts with absolute paths."""
        # Use absolute paths to ensure hooks work from any working directory
        base_dir = str(self.project_root)
        claude_map_dir = str(self.claude_map_dir)

        # Post-tool-use hook
        hook_content = f'''#!/bin/bash
# Codebase Cartographer - Auto-update hook
# Queues file updates when Edit/Write tools are used

BASE_DIR="{base_dir}"
CLAUDE_MAP_DIR="{claude_map_dir}"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\\([^"]*\\)"$/\\1/')

case "$TOOL_NAME" in
    Edit|Write|NotebookEdit)
        FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\\([^"]*\\)"$/\\1/')
        if [ -n "$FILE_PATH" ] && [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ]; then
            mkdir -p "${{CLAUDE_MAP_DIR}}/cache"
            echo "$FILE_PATH" >> "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null || true
        fi
        ;;
esac
exit 0
'''
        hook_path = self.claude_dir / 'hooks' / 'cartographer-update.sh'
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
        print("    + Installed hook: cartographer-update.sh")

        # Stop hook
        stop_content = f'''#!/bin/bash
# Codebase Cartographer - Session end hook
# Processes queued updates when session ends

BASE_DIR="{base_dir}"
CLAUDE_MAP_DIR="{claude_map_dir}"
CLAUDE_MAP="${{CLAUDE_MAP_DIR}}/bin/claude-map"

if [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ] && [ -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" ]; then
    "$CLAUDE_MAP" update 2>/dev/null || true
    rm -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null || true
fi
exit 0
'''
        stop_path = self.claude_dir / 'hooks' / 'cartographer-finalize.sh'
        stop_path.write_text(stop_content)
        stop_path.chmod(0o755)
        print("    + Installed hook: cartographer-finalize.sh")

    def _install_commands(self):
        """Install slash command definitions."""
        # Use absolute path to avoid issues when Claude changes working directory
        claude_map_bin = str(self.claude_map_dir / 'bin' / 'claude-map')

        cmd_content = f'''# /map - Codebase Cartographer

Manage the codebase map for token-efficient exploration.

## Usage
- `/map` or `/map update` - Update the map
- `/map init` - Initialize mapping (first time)
- `/map stats` - Show statistics
- `/map find <name>` - Quick search

## Execution
Run: `{claude_map_bin} <subcommand>`
'''
        cmd_path = self.claude_dir / 'commands' / 'map.md'
        cmd_path.write_text(cmd_content)
        print("    + Installed command: /map")

    def _update_claude_md(self):
        """Update or create project CLAUDE.md with cartographer instructions at top."""
        claude_md = self.project_root / 'CLAUDE.md'

        # Use absolute path to avoid issues when Claude changes working directory
        claude_map_bin = str(self.claude_map_dir / 'bin' / 'claude-map')

        # Markers for identifying and updating the cartographer section
        start_marker = '<!-- CARTOGRAPHER_START -->'
        end_marker = '<!-- CARTOGRAPHER_END -->'

        cartographer_section = f'''{start_marker}
## CRITICAL: Use Codebase Cartographer First

**BEFORE using Read, Grep, or Glob tools to explore code, use the cartographer.** It saves 95%+ tokens compared to reading full files and returns precise line numbers and signatures.

**In Planning Mode:** When using EnterPlanMode, your FIRST action should be to use the cartographer to understand the codebase structure before designing your implementation approach.

**Workflow:**
1. Use cartographer to find file paths and line numbers
2. Use `Read` tool with specific line range only if you need full implementation details

**Fallback:** If cartographer returns no results, use native Grep/Glob/Read tools.

### Quick Reference
```bash
{claude_map_bin} find <name>      # Find by name (fastest)
{claude_map_bin} query "<text>"   # Pattern-based search
{claude_map_bin} show <file>      # File structure
{claude_map_bin} exports          # List public API
```

For full command options, query patterns, and pagination: use the `cartographer` skill.
{end_marker}'''

        if claude_md.exists():
            content = claude_md.read_text()

            # Check if we need to update an existing section
            if start_marker in content and end_marker in content:
                # Replace existing cartographer section
                pattern = re.escape(start_marker) + r'.*?' + re.escape(end_marker)
                new_content = re.sub(pattern, cartographer_section, content, flags=re.DOTALL)
                claude_md.write_text(new_content)
                print("    + Updated CLAUDE.md (refreshed cartographer section)")
            elif 'Codebase Cartographer' not in content:
                # Insert after the first header line, not at the end
                lines = content.split('\n')
                insert_idx = 0

                # Find the end of the first header block (# Title + optional blank line)
                for i, line in enumerate(lines):
                    if line.startswith('# '):
                        insert_idx = i + 1
                        # Skip any blank lines after the header
                        while insert_idx < len(lines) and lines[insert_idx].strip() == '':
                            insert_idx += 1
                        break

                # Insert the cartographer section with blank line after
                lines.insert(insert_idx, '\n' + cartographer_section + '\n')
                claude_md.write_text('\n'.join(lines))
                print("    + Updated CLAUDE.md (inserted at top)")
            else:
                print("    = CLAUDE.md already has cartographer section (add markers to enable updates)")
        else:
            # Create new CLAUDE.md
            claude_md.write_text(f"# Project Instructions\n\n{cartographer_section}\n")
            print("    + Created CLAUDE.md")

    def _update_settings(self):
        """Update .claude/settings.json with hook configuration using absolute paths."""
        settings_path = self.claude_dir / 'settings.json'

        # Use absolute paths for hook commands
        update_hook_cmd = str(self.claude_dir / 'hooks' / 'cartographer-update.sh')
        finalize_hook_cmd = str(self.claude_dir / 'hooks' / 'cartographer-finalize.sh')

        # Load existing or create new
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except:
                settings = {}
        else:
            settings = {}

        # Add/update hooks configuration
        if 'hooks' not in settings:
            settings['hooks'] = {}

        # PostToolUse hooks (matcher is pipe-separated string, hooks are command objects)
        post_tool_hooks = settings['hooks'].get('PostToolUse', [])
        cartographer_hook = {
            "matcher": "Edit|Write|NotebookEdit",
            "hooks": [
                {
                    "type": "command",
                    "command": update_hook_cmd
                }
            ]
        }

        # Check if already configured (check for any cartographer-update.sh path)
        hook_exists = any(
            any('cartographer-update.sh' in h.get('command', '')
                for h in hook_entry.get('hooks', []) if isinstance(h, dict))
            for hook_entry in post_tool_hooks if isinstance(hook_entry, dict)
        )

        if not hook_exists:
            post_tool_hooks.append(cartographer_hook)
            settings['hooks']['PostToolUse'] = post_tool_hooks

        # Stop hooks (empty matcher string matches all)
        stop_hooks = settings['hooks'].get('Stop', [])
        stop_hook = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": finalize_hook_cmd
                }
            ]
        }

        # Check if already configured (check for any cartographer-finalize.sh path)
        stop_exists = any(
            any('cartographer-finalize.sh' in h.get('command', '')
                for h in hook_entry.get('hooks', []) if isinstance(h, dict))
            for hook_entry in stop_hooks if isinstance(hook_entry, dict)
        )

        if not stop_exists:
            stop_hooks.append(stop_hook)
            settings['hooks']['Stop'] = stop_hooks

        # Add permissions to whitelist cartographer commands
        # Use absolute path for the command pattern
        claude_map_cmd = str(self.claude_map_dir / 'bin' / 'claude-map')
        cartographer_permissions = [
            f"Bash({claude_map_cmd}:*)",  # All claude-map subcommands
        ]

        # Initialize permissions if not present
        if 'permissions' not in settings:
            settings['permissions'] = {}
        if 'allow' not in settings['permissions']:
            settings['permissions']['allow'] = []

        # Append our permissions (avoid duplicates)
        existing_allows = settings['permissions']['allow']
        for perm in cartographer_permissions:
            if perm not in existing_allows:
                existing_allows.append(perm)

        settings['permissions']['allow'] = existing_allows
        print(f"    + Whitelisted cartographer commands")

        # Write settings
        settings_path.write_text(json.dumps(settings, indent=2))
        print("    + Updated settings.json")


def install_claude_integration(project_root: str = None) -> bool:
    """Main entry point for Claude integration installation."""
    if project_root is None:
        project_root = os.getcwd()

    installer = ClaudeIntegrationInstaller(Path(project_root))
    return installer.install()


if __name__ == '__main__':
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    success = install_claude_integration(project)
    sys.exit(0 if success else 1)
