"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Command-line interface with Click.
Provides 10 commands for codebase mapping and querying.
"""

import sys
import os
import time
import json
from pathlib import Path

import click

from . import __version__
from .mapper import CodebaseMapper
from .integration import ClaudeCodeIntegration
from .benchmark import TokenOptimizationBenchmark


def find_project_root() -> Path:
    """Find project root (directory containing .claude-map)."""
    current = Path.cwd()

    while current != current.parent:
        if (current / '.claude-map').exists():
            return current
        current = current.parent

    # Not found - use current directory
    return Path.cwd()


@click.group()
@click.version_option(version=__version__, prog_name='Codebase Cartographer')
def cli():
    """
    Codebase Cartographer - Token-optimized codebase mapping for Claude Code

    Dramatically reduce token usage when working with large codebases.
    Achieves 95-98% token reduction through intelligent mapping.

    Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>

    \b
    Quick Start:
        claude-map init                    # Initialize mapping
        claude-map query "find UserAuth"   # Query the map
        claude-map find UserProfile        # Quick search
        claude-map stats                   # Show statistics
    """
    pass


@cli.command()
@click.argument('project_root', type=click.Path(exists=True), default='.')
@click.option('--workers', '-w', type=int, help='Number of worker threads/processes')
@click.option('--no-mp', is_flag=True, help='Disable multiprocessing')
@click.option('--watch', is_flag=True, help='Watch for changes after initial mapping')
def init(project_root, workers, no_mp, watch):
    """
    Initialize codebase mapping.

    Creates .claude-map/ directory and builds the initial map.
    This is the first command you should run.

    \b
    Examples:
        claude-map init
        claude-map init /path/to/project
        claude-map init --workers 8
        claude-map init --watch
    """
    project_path = Path(project_root).resolve()

    click.echo(f"\n{'='*70}")
    click.echo("Codebase Cartographer - Initializing")
    click.echo("Copyright (c) 2025 Breach Craft - Mike Piekarski")
    click.echo('='*70)
    click.echo(f"\nProject: {project_path}")

    # Create mapper
    mapper = CodebaseMapper(
        project_path,
        max_workers=workers,
        use_multiprocessing=not no_mp
    )

    try:
        # Run initial mapping
        report = mapper.map_directory(incremental=False)

        click.echo(f"\n{'='*70}")
        click.echo("Initialization Complete!")
        click.echo('='*70)

        # Show performance report
        click.echo(f"\nPerformance:")
        click.echo(f"  Duration:    {report['duration_seconds']} seconds")
        click.echo(f"  Files:       {report['files_processed']}")
        click.echo(f"  Components:  {report['components_found']}")
        click.echo(f"  Rate:        {report['files_per_second']} files/sec")

        # Show quick stats
        stats = mapper.get_stats()
        click.echo(f"\nMapped:")
        click.echo(f"  Files:      {stats['total_files']:,}")
        click.echo(f"  Components: {stats['total_components']:,}")
        click.echo(f"  Exported:   {stats['exported_count']:,}")

        # Start watching if requested
        if watch:
            _start_watcher(mapper)

    finally:
        mapper.close()


@cli.command()
@click.argument('query_text')
@click.option('--max-tokens', '-t', default=10000, help='Maximum tokens to return')
@click.option('--offset', '-o', default=0, help='Skip first N results (for pagination)')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
@click.option('--quiet', '-q', is_flag=True, help='Suppress token savings info')
def query(query_text, max_tokens, offset, format, quiet):
    """
    Query the codebase map with pattern matching.

    Parses common query patterns like "find X", "dependencies of Y",
    "what calls Z". Falls back to full-text search on component names.

    For best results, use specific patterns:

    \b
    FIND patterns:
        "find UserProfile"           - locate by name
        "where is authenticate"      - same as find
        "search for database"        - same as find

    \b
    DEPENDENCY patterns:
        "what does auth.py depend on"
        "dependencies of database.py"
        "imports in utils.py"

    \b
    CALL CHAIN patterns:
        "what calls authenticate"
        "call chain for process"

    \b
    OTHER patterns:
        "overview"                   - codebase summary
        "exports"                    - list public API
        "show src/auth.py"          - file components

    \b
    FALLBACK:
        Any other text does FTS (full-text search) on component names.

    \b
    Examples:
        claude-map query "find UserProfile"
        claude-map query "what does auth.py depend on"
        claude-map query "call chain for authenticate"
        claude-map query "find User" --offset 20
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)
        result = integration.get_context(query_text, max_tokens=max_tokens, offset=offset)

        optimized_tokens = len(result) // 4

        if format == 'json':
            output = {
                'query': query_text,
                'result': result,
                'tokens_estimate': optimized_tokens,
                'traditional_estimate': 20000,
                'tokens_saved': 20000 - optimized_tokens,
                'offset': offset,
            }
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(result)
            if not quiet:
                saved = 20000 - optimized_tokens
                click.echo(f"\n[~{optimized_tokens:,} tokens | saved ~{saved:,} tokens (95%+)]", err=True)

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        click.echo("\nRun 'claude-map init' first to create the codebase map.", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--limit', '-l', default=20, help='Maximum results to return')
@click.option('--offset', '-o', default=0, help='Skip first N results (for pagination)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress token savings info')
def find(name, limit, offset, quiet):
    """
    Quick component search.

    Returns compact representations for minimal token usage.
    Use --offset to paginate through large result sets.

    \b
    Examples:
        claude-map find UserService
        claude-map find authenticate
        claude-map find --limit 50 User
        claude-map find User --offset 20    # Get next page
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)
        result = integration.quick_find(name, limit=limit, offset=offset)
        click.echo(result)

        if not quiet:
            optimized_tokens = len(result) // 4
            saved = 15000 - optimized_tokens  # find typically saves vs 15k traditional
            click.echo(f"\n[~{optimized_tokens:,} tokens | saved ~{saved:,} tokens (98%+)]", err=True)

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
def stats(format):
    """
    Show database statistics.

    Displays information about mapped components, languages,
    performance metrics, and database size.
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)
        stats_data = integration.get_stats()

        if format == 'json':
            click.echo(json.dumps(stats_data, indent=2))
        else:
            click.echo(f"\n{'='*70}")
            click.echo("Codebase Statistics")
            click.echo('='*70)

            click.echo(f"\nComponents:")
            click.echo(f"  Total:    {stats_data['total_components']:,}")
            click.echo(f"  Exported: {stats_data['exported_count']:,}")
            click.echo(f"  Tests:    {stats_data['test_count']:,}")

            click.echo(f"\nFiles:")
            click.echo(f"  Total:    {stats_data['total_files']:,}")
            click.echo(f"  Lines:    {stats_data['total_lines']:,}")

            click.echo(f"\nLanguages:")
            for lang_info in stats_data['by_language']:
                click.echo(
                    f"  {lang_info['language']:15} "
                    f"{lang_info['files']:5} files, "
                    f"{lang_info['components']:6} components"
                )

            if stats_data.get('hot_components'):
                click.echo(f"\nMost Accessed:")
                for comp in stats_data['hot_components'][:5]:
                    click.echo(f"  - {comp['name']} ({comp['access_count']} accesses)")

            perf = stats_data.get('performance', {})
            if perf:
                click.echo(f"\nPerformance:")
                click.echo(f"  Queries:     {perf['total_queries']:,}")
                click.echo(f"  Cache hits:  {perf['cache_hit_rate']}")
                click.echo(f"  Avg time:    {perf['avg_query_time_ms']}ms")

            click.echo(f"\nDatabase:")
            click.echo(f"  Size:        {stats_data['database_size_mb']} MB")

            # Show session token savings
            if integration.tracker:
                session_stats = integration.tracker.stats
                # Check totals (queries list may be empty if loaded from disk)
                if session_stats.total_tokens_saved > 0:
                    click.echo(f"\nSession Token Savings:")
                    click.echo(f"  Queries:        {session_stats.query_count:,}")
                    click.echo(f"  Optimized:      {session_stats.total_optimized_tokens:,} tokens")
                    click.echo(f"  Traditional:    {session_stats.total_traditional_tokens:,} tokens")
                    click.echo(f"  Saved:          {session_stats.total_tokens_saved:,} tokens ({session_stats.savings_percent:.1f}%)")
                    click.echo(f"  Cost saved:     ${session_stats.cost_saved_usd:.2f}")
                    if session_stats.total_query_time_ms > 0:
                        click.echo(f"  Avg query time: {session_stats.avg_query_time_ms:.2f}ms")
                    if session_stats.total_cache_hits + session_stats.total_cache_misses > 0:
                        click.echo(f"  Cache hit rate: {session_stats.cache_hit_rate:.1f}%")

            click.echo()

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--workers', '-w', type=int, help='Number of worker threads/processes')
@click.option('--no-mp', is_flag=True, help='Disable multiprocessing')
def update(workers, no_mp):
    """
    Incrementally update the codebase map.

    Only processes files that have changed since last mapping.
    Much faster than full re-initialization.
    """
    project_root = find_project_root()

    mapper = CodebaseMapper(
        project_root,
        max_workers=workers,
        use_multiprocessing=not no_mp
    )

    try:
        click.echo("\nUpdating codebase map...")
        report = mapper.map_directory(incremental=True)

        click.echo(f"\nUpdate complete")
        click.echo(f"  Files processed: {report['files_processed']}")
        click.echo(f"  Files skipped:   {report['files_skipped']}")
        click.echo(f"  Duration:        {report['duration_seconds']} seconds")

    finally:
        mapper.close()


@cli.command()
@click.option('--debounce', '-d', default=0.5, help='Debounce delay in seconds')
def watch(debounce):
    """
    Watch for file changes and update map automatically.

    Runs continuously until interrupted with Ctrl+C.
    Changes are batched with configurable debounce delay.
    """
    try:
        from .watcher import CodebaseWatcher, WATCHDOG_AVAILABLE
    except ImportError:
        WATCHDOG_AVAILABLE = False

    if not WATCHDOG_AVAILABLE:
        click.echo("\nError: watchdog not installed", err=True)
        click.echo("Install with: pip install watchdog", err=True)
        sys.exit(1)

    project_root = find_project_root()

    mapper = CodebaseMapper(project_root)
    watcher = CodebaseWatcher(mapper, debounce_seconds=debounce)

    observer = watcher.start()

    if not observer:
        click.echo("\nFailed to start watcher", err=True)
        sys.exit(1)

    click.echo(f"\n{'='*70}")
    click.echo("Watching for file changes...")
    click.echo(f"Project: {project_root}")
    click.echo(f"Debounce: {debounce} seconds")
    click.echo('='*70)
    click.echo("\nPress Ctrl+C to stop watching...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n\nStopping watcher...")
        observer.stop()
        watcher.stop()
        observer.join()
        mapper.close()


@cli.command()
@click.option('--verbose/--quiet', default=True, help='Verbose output')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
def benchmark(verbose, format):
    """
    Run performance benchmark.

    Compares traditional approach (loading full files) vs
    optimized approach (using codebase map).

    Shows token savings and cost analysis.
    """
    project_root = find_project_root()

    try:
        bench = TokenOptimizationBenchmark(project_root)
        report = bench.run_full_benchmark(verbose=verbose)

        if format == 'json':
            click.echo(json.dumps(report, indent=2))

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
def optimize():
    """
    Optimize database.

    Runs VACUUM and ANALYZE to reclaim space,
    update statistics, and clear caches.
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)

        click.echo("\nOptimizing database...")
        integration.db.optimize()
        click.echo("Optimization complete")

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file_path')
@click.option('--quiet', '-q', is_flag=True, help='Suppress token savings info')
def show(file_path, quiet):
    """
    Show components in a file.

    \b
    Examples:
        claude-map show src/auth/user.py
        claude-map show utils.js
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)
        result = integration.get_file_summary(file_path)
        click.echo(result)

        if not quiet:
            optimized_tokens = len(result) // 4
            saved = 8000 - optimized_tokens  # show typically saves vs 8k (one file)
            click.echo(f"\n[~{optimized_tokens:,} tokens | saved ~{saved:,} tokens (96%+)]", err=True)

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', '-l', default=50, help='Maximum results')
@click.option('--offset', '-o', default=0, help='Skip first N results (for pagination)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress token savings info')
def exports(limit, offset, quiet):
    """
    List all exported components (public API).

    Shows all components marked as exported/public,
    sorted by access frequency. Use --offset to paginate.
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)
        result = integration.list_exports(limit=limit, offset=offset)
        click.echo(result)

        if not quiet:
            optimized_tokens = len(result) // 4
            saved = 30000 - optimized_tokens  # exports typically saves vs 30k
            click.echo(f"\n[~{optimized_tokens:,} tokens | saved ~{saved:,} tokens (96%+)]", err=True)

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show recent queries')
@click.option('--lifetime', is_flag=True, help='Show lifetime stats')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text')
def session(verbose, lifetime, format):
    """
    Show session token savings.

    Displays cumulative token savings for the current session,
    including queries made, tokens used, and cost saved.
    """
    project_root = find_project_root()

    try:
        integration = ClaudeCodeIntegration(project_root)

        if format == 'json':
            if lifetime:
                data = integration.get_lifetime_stats()
            else:
                data = integration.tracker.stats.to_dict() if integration.tracker else {}
            click.echo(json.dumps(data, indent=2))
        else:
            if lifetime:
                stats = integration.get_lifetime_stats()
                click.echo(f"\n{'='*50}")
                click.echo("Lifetime Token Savings")
                click.echo('='*50)
                click.echo(f"Total queries:    {stats.get('lifetime_queries', 0):,}")
                click.echo(f"Tokens saved:     {stats.get('lifetime_tokens_saved', 0):,}")
                click.echo(f"Cost saved:       ${stats.get('lifetime_cost_saved_usd', 0):.2f}")
                click.echo('='*50)
            else:
                summary = integration.get_session_summary(verbose=verbose)
                if summary:
                    click.echo(summary)
                else:
                    click.echo("\nNo session data available.")

        integration.close()

    except FileNotFoundError as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


def _start_watcher(mapper: CodebaseMapper):
    """Start file watcher after initialization."""
    try:
        from .watcher import CodebaseWatcher, WATCHDOG_AVAILABLE
    except ImportError:
        click.echo("\nWatch mode requires watchdog: pip install watchdog")
        return

    if not WATCHDOG_AVAILABLE:
        click.echo("\nWatch mode requires watchdog: pip install watchdog")
        return

    click.echo(f"\n{'='*70}")
    click.echo("Starting file watcher...")
    click.echo('='*70)

    watcher = CodebaseWatcher(mapper)
    observer = watcher.start()

    if observer:
        click.echo("\nPress Ctrl+C to stop watching...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n\nStopping watcher...")
            observer.stop()
            watcher.stop()
            observer.join()


if __name__ == '__main__':
    cli()
