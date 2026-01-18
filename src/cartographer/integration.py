"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Claude Code integration layer.
Provides token-budgeted queries and natural language interface.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .database import TokenOptimizedDatabase
from .session_tracker import SessionTracker


class ClaudeCodeIntegration:
    """
    Primary integration point for Claude Code.

    This class provides token-optimized queries for codebase exploration.
    All methods are designed to return minimal tokens while providing
    maximum useful information.

    Usage:
        integration = ClaudeCodeIntegration('/path/to/project')
        context = integration.get_context("find authentication", max_tokens=2000)
        result = integration.quick_find("UserProfile")
        summary = integration.get_file_summary("src/auth.py")
    """

    def __init__(self, project_root: Path, track_session: bool = True):
        self.project_root = Path(project_root).resolve()
        self.claude_dir = self.project_root / '.claude-map'
        self.db_path = self.claude_dir / 'codebase.db'

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Codebase map not found at {self.db_path}. "
                f"Run 'claude-map init' first."
            )

        self.db = TokenOptimizedDatabase(self.db_path)

        # Session tracking for token savings
        self.tracker = SessionTracker(self.project_root) if track_session else None

    def get_context(self, query: str, max_tokens: int = 10000, offset: int = 0) -> str:
        """
        Primary method for getting context from the codebase.

        Parses natural language query to determine intent and returns
        appropriate token-budgeted response.

        Supported intents:
            - overview: Codebase overview
            - find <name>: Find components by name
            - detail <name>: Get detailed info about component
            - dependencies <file>: Get file dependencies
            - calls <func>: Get call chain for function
            - search <query>: Full-text search
            - file <path>: Get file summary
            - exports: List exported components

        Args:
            query: Natural language query
            max_tokens: Maximum tokens to return
            offset: Skip first N results (for pagination)

        Returns:
            Token-optimized context string with pagination info when truncated
        """
        query_lower = query.lower().strip()
        intent, target = self._parse_intent(query_lower)

        # Track timing and cache
        start_time = time.time()
        cache_hits_before = self.db.cache_hits

        if intent == 'overview':
            result = self._get_overview(max_tokens)
        elif intent == 'find':
            result = self._get_find_results(target, max_tokens, offset)
        elif intent == 'detail':
            result = self._get_component_detail(target, max_tokens)
        elif intent == 'dependencies':
            result = self._get_dependencies(target, max_tokens)
        elif intent == 'calls':
            result = self._get_call_chain(target, max_tokens)
        elif intent == 'search':
            result = self._get_search_results(target, max_tokens, offset)
        elif intent == 'file':
            result = self._get_file_summary(target, max_tokens)
        elif intent == 'exports':
            result = self._get_exports(max_tokens, offset)
        else:
            # Default to search
            intent = 'search'
            result = self._get_search_results(query, max_tokens, offset)

        # Track token savings with timing and cache info
        self._track_query(intent, query, result, start_time, cache_hits_before)

        return result

    def _parse_intent(self, query: str) -> Tuple[str, str]:
        """Parse query to determine intent and target.

        Handles natural language variations for:
        - find: locate specific components by name
        - detail: get detailed info about a component
        - dependencies: file/module dependencies
        - calls: call chain analysis
        - file: show file structure
        - exports: list public API
        - overview: codebase structure overview
        - search: fallback FTS search
        """
        query_lower = query.lower()

        # Overview patterns
        if any(p in query_lower for p in ['overview', 'structure', 'architecture', 'what is this', 'codebase summary']):
            return 'overview', ''

        # Export/list patterns (check before find to catch "list all X")
        export_patterns = [
            r'list\s+(?:all\s+)?(?:exported|public)\s+',
            r'list\s+(?:all\s+)?exports',
            r'list\s+(?:all\s+)?components',
            r'show\s+(?:all\s+)?exports',
            r'public\s+api',
            r'public\s+interface',
            r'exported\s+(?:functions|classes|components)',
        ]
        for pattern in export_patterns:
            if re.search(pattern, query_lower):
                return 'exports', ''

        # Dependencies patterns - check before find/detail to catch "what does X depend on"
        # Order matters: more specific patterns first to avoid greedy matching
        dep_patterns = [
            # Specific "what does X depend/import" patterns first
            r'what\s+does\s+([^\s]+)\s+(?:depend|import|use|require)',
            r'what\s+(?:are|does)\s+([^\s]+)\s+import',
            # File extension patterns
            r'([^\s]+\.(?:py|js|ts|go|rb))\s+depend',
            # Require preposition to avoid matching "depend on" -> "on"
            r'dependencies\s+(?:of|for|in)\s+([^\s]+)',
            r'imports?\s+(?:of|for|in)\s+([^\s]+)',
        ]
        for pattern in dep_patterns:
            if match := re.search(pattern, query, re.IGNORECASE):
                return 'dependencies', match.group(1)

        # Find patterns - expanded set (use re.IGNORECASE to preserve original case)
        find_patterns = [
            r'find\s+(?:the\s+)?(\w+)',
            r'where\s+is\s+(?:the\s+)?(\w+)',
            r'locate\s+(?:the\s+)?(\w+)',
            r'show\s+me\s+(?:the\s+)?(\w+)',
            r'look\s+for\s+(?:the\s+)?(\w+)',
            r'search\s+for\s+(?:the\s+)?(\w+)',
            r'get\s+(?:the\s+)?(\w+)',
        ]
        for pattern in find_patterns:
            if match := re.search(pattern, query, re.IGNORECASE):
                target = match.group(1)
                # Skip common words that aren't component names
                if target.lower() not in ('the', 'a', 'an', 'all', 'any', 'some', 'function', 'class', 'method', 'component'):
                    return 'find', target

        # Detail patterns
        detail_patterns = [
            r'detail(?:s)?\s+(?:for\s+|about\s+|of\s+)?(\w+)',
            r'explain\s+(?:the\s+)?(\w+)',
            r'what\s+(?:is|does)\s+(?:the\s+)?(\w+)',
            r'describe\s+(?:the\s+)?(\w+)',
            r'tell\s+me\s+about\s+(\w+)',
            r'info\s+(?:on|about)\s+(\w+)',
        ]
        for pattern in detail_patterns:
            if match := re.search(pattern, query_lower):
                return 'detail', match.group(1)

        # Call chain patterns
        call_patterns = [
            r'call(?:s|ed)?\s+(?:by|to|from)?\s*(\w+)',
            r'who\s+calls\s+(\w+)',
            r'what\s+calls\s+(\w+)',
            r'call\s+chain\s+(?:for\s+)?(\w+)',
            r'callers\s+of\s+(\w+)',
            r'(\w+)\s+call\s+chain',
        ]
        for pattern in call_patterns:
            if match := re.search(pattern, query_lower):
                return 'calls', match.group(1)

        # File patterns
        file_patterns = [
            r'file\s+([^\s]+)',
            r'show\s+([^\s]+\.(?:py|js|ts|go|rb|jsx|tsx))',
            r'in\s+([^\s]+\.(?:py|js|ts|go|rb|jsx|tsx))',
            r'components?\s+in\s+([^\s]+)',
        ]
        for pattern in file_patterns:
            if match := re.search(pattern, query_lower):
                return 'file', match.group(1)

        # Default to search with improved term extraction
        terms = self._extract_search_terms(query)
        return 'search', ' '.join(terms) if terms else query

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from query.

        Filters out:
        - Common English stop words
        - Query action words (find, show, list, etc.)
        - Articles and prepositions

        Returns lowercase terms for FTS matching.
        """
        # Extended stop words including query action words
        stop_words = {
            # Common English
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'shall', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'and', 'or',
            'but', 'if', 'because', 'until', 'while', 'about',
            # Query action words
            'find', 'show', 'list', 'get', 'search', 'locate', 'look',
            'display', 'give', 'tell', 'what', 'which', 'who', 'whom',
            'this', 'that', 'these', 'those', 'me', 'my', 'your',
        }

        words = re.findall(r'\w+', query.lower())
        # Filter stop words and very short words (likely not component names)
        terms = [w for w in words if w not in stop_words and len(w) > 2]

        return terms

    def _get_overview(self, max_tokens: int) -> str:
        """Get codebase overview."""
        stats = self.db.get_stats()

        lines = [
            "# Codebase Overview",
            "",
            f"**Total Files**: {stats['total_files']}",
            f"**Total Lines**: {stats['total_lines']:,}",
            f"**Components**: {stats['total_components']}",
            f"**Exported (Public)**: {stats['exported_count']}",
            "",
            "## Languages",
        ]

        for lang in stats['by_language'][:10]:
            lines.append(f"- {lang['language']}: {lang['files']} files, {lang['components']} components")

        if stats['hot_components']:
            lines.append("")
            lines.append("## Frequently Accessed")
            for comp in stats['hot_components'][:5]:
                lines.append(f"- {comp['name']} ({comp['type']})")

        # Truncate if needed
        result = '\n'.join(lines)
        estimated_tokens = len(result) // 4

        if estimated_tokens > max_tokens:
            # Truncate to fit
            lines = lines[:15]
            result = '\n'.join(lines) + "\n\n... (truncated)"

        return result

    def _get_find_results(self, name: str, max_tokens: int, offset: int = 0) -> str:
        """Find components by name with pagination support."""
        limit = max(max_tokens // 50, 10)  # Estimate ~50 tokens per result
        return self.db.query_compact(name, limit=limit, offset=offset)

    def _get_component_detail(self, name: str, max_tokens: int) -> str:
        """Get detailed component information."""
        summary = self.db.query_summary(name)

        if max_tokens > 400:
            # Can include more details
            details = self.db.get_details(name)
            if details:
                lines = [summary, "", "## Additional Details"]

                if details.get('docstring'):
                    lines.append(f"\n**Docstring**:\n{details['docstring'][:500]}")

                if details.get('params'):
                    lines.append("\n**Parameters**:")
                    for p in details['params'][:10]:
                        ptype = p.get('type', 'any')
                        lines.append(f"  - {p['name']}: {ptype}")

                if details.get('methods'):
                    lines.append("\n**Methods**:")
                    for m in details['methods'][:15]:
                        lines.append(f"  - {m}")

                return '\n'.join(lines)

        return summary

    def _get_dependencies(self, target: str, max_tokens: int) -> str:
        """Get file dependencies."""
        return self.db.get_dependencies(target)

    def _get_call_chain(self, func_name: str, max_tokens: int) -> str:
        """Get call chain for a function."""
        depth = 3 if max_tokens > 500 else 2
        return self.db.get_call_chain(func_name, max_depth=depth)

    def _get_search_results(self, query: str, max_tokens: int, offset: int = 0) -> str:
        """Full-text search with pagination support."""
        limit = max(max_tokens // 50, 10)
        return self.db.search_fts(query, limit=limit, offset=offset)

    def _get_file_summary(self, file_path: str, max_tokens: int) -> str:
        """Get file summary."""
        return self.db.get_file_components(file_path)

    def _get_exports(self, max_tokens: int, offset: int = 0) -> str:
        """Get exported components with pagination support."""
        limit = max(max_tokens // 50, 20)
        return self.db.list_exports(limit=limit, offset=offset)

    # ================================================================
    # PERFORMANCE TRACKING HELPER
    # ================================================================

    def _track_query(self, query_type: str, query: str, result: str, start_time: float, cache_hits_before: int):
        """Track a query with timing and cache info."""
        if not self.tracker:
            return

        query_time_ms = (time.time() - start_time) * 1000
        optimized_tokens = len(result) // 4

        # Determine if we got a cache hit (cache_hits increased)
        cache_hit = self.db.cache_hits > cache_hits_before

        self.tracker.record_query(
            query_type,
            query,
            optimized_tokens,
            query_time_ms=query_time_ms,
            cache_hit=cache_hit,
        )

    # ================================================================
    # CONVENIENCE METHODS
    # ================================================================

    def quick_find(self, name: str, limit: int = 10, offset: int = 0) -> str:
        """
        Quick search for a component by name.
        Returns compact representations for minimal tokens.
        Supports pagination via offset parameter.
        """
        start_time = time.time()
        cache_hits_before = self.db.cache_hits

        result = self.db.query_compact(name, limit=limit, offset=offset)

        self._track_query('find', name, result, start_time, cache_hits_before)
        return result

    def get_file_summary(self, file_path: str) -> str:
        """Get summary of components in a file."""
        start_time = time.time()
        cache_hits_before = self.db.cache_hits

        result = self.db.get_file_components(file_path)

        self._track_query('show', file_path, result, start_time, cache_hits_before)
        return result

    def list_exports(self, limit: int = 50, offset: int = 0) -> str:
        """List all exported (public) components with pagination support."""
        start_time = time.time()
        cache_hits_before = self.db.cache_hits

        result = self.db.list_exports(limit=limit, offset=offset)

        self._track_query('exports', '', result, start_time, cache_hits_before)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_stats()

    def get_component_summary(self, name: str) -> str:
        """Get summary representation of a component."""
        return self.db.query_summary(name)

    def get_component_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full details of a component."""
        return self.db.get_details(name)

    def get_dependencies(self, file_path: str) -> str:
        """Get dependencies for a file."""
        return self.db.get_dependencies(file_path)

    def get_call_chain(self, func_name: str, depth: int = 3) -> str:
        """Get call chain for a function."""
        return self.db.get_call_chain(func_name, max_depth=depth)

    def search(self, query: str, limit: int = 20, offset: int = 0) -> str:
        """Full-text search across codebase with pagination support."""
        return self.db.search_fts(query, limit=limit, offset=offset)

    def get_test_coverage(self) -> str:
        """Get overview of test components."""
        cursor = self.db.conn.execute("""
            SELECT compact FROM component_index
            WHERE is_test = 1
            ORDER BY access_count DESC, name
            LIMIT 30
        """)

        rows = cursor.fetchall()

        if rows:
            lines = ["Test Components:", ""]
            for row in rows:
                lines.append(f"  {row['compact']}")
            return '\n'.join(lines)

        return "No test components found"

    def close(self):
        """Close database connection."""
        self.db.close()

    # ================================================================
    # SESSION TRACKING METHODS
    # ================================================================

    def get_session_summary(self, verbose: bool = False) -> str:
        """Get session token savings summary."""
        if self.tracker:
            return self.tracker.get_summary(verbose=verbose)
        return ""

    def get_session_inline(self) -> str:
        """Get short inline session summary."""
        if self.tracker:
            return self.tracker.get_inline_summary()
        return ""

    def get_lifetime_stats(self) -> Dict[str, Any]:
        """Get lifetime token savings statistics."""
        if self.tracker:
            return self.tracker.get_lifetime_stats()
        return {}

    def end_session(self):
        """End the session and archive stats."""
        if self.tracker:
            self.tracker.end_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
