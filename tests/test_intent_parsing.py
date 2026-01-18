"""Tests for natural language intent parsing."""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cartographer.integration import ClaudeCodeIntegration


class TestIntentParsing:
    """Test the _parse_intent method."""

    @pytest.fixture
    def integration(self, tmp_path):
        """Create integration with mock database."""
        # Create minimal database structure
        db_path = tmp_path / ".claude-map"
        db_path.mkdir()
        (db_path / "codebase.db").touch()
        return ClaudeCodeIntegration(tmp_path)

    def test_find_intent_variations(self, integration):
        """Test various 'find' intent phrasings."""
        test_cases = [
            ("find UserProfile", ("find", "UserProfile")),
            ("where is UserProfile", ("find", "UserProfile")),
            ("locate the authenticate function", ("find", "authenticate")),
            ("show me the UserService class", ("find", "UserService")),
            ("look for LoginHandler", ("find", "LoginHandler")),
            ("search for database", ("find", "database")),
        ]
        for query, expected in test_cases:
            result = integration._parse_intent(query)
            assert result == expected, f"Query '{query}' returned {result}, expected {expected}"

    def test_list_intent(self, integration):
        """Test 'list' intent patterns - should map to exports or search."""
        test_cases = [
            ("list all components", ("exports", "")),
            ("list exported functions", ("exports", "")),
            ("list public API", ("exports", "")),
            ("show all exports", ("exports", "")),
        ]
        for query, expected in test_cases:
            result = integration._parse_intent(query)
            assert result == expected, f"Query '{query}' returned {result}, expected {expected}"

    def test_dependency_intent(self, integration):
        """Test dependency query patterns."""
        test_cases = [
            ("what does auth.py depend on", ("dependencies", "auth.py")),
            ("dependencies of database.py", ("dependencies", "database.py")),
            ("imports in utils.py", ("dependencies", "utils.py")),
            ("what does UserService import", ("dependencies", "UserService")),
        ]
        for query, expected in test_cases:
            result = integration._parse_intent(query)
            assert result == expected, f"Query '{query}' returned {result}, expected {expected}"

    def test_search_term_extraction(self, integration):
        """Test that search term extraction filters unhelpful words."""
        test_cases = [
            # (query, expected_terms)
            ("find authentication handler", ["authentication", "handler"]),
            ("list all users in system", ["users", "system"]),  # removes "list", "all", "in"
            ("the database connection pool", ["database", "connection", "pool"]),
            ("UserProfile component", ["userprofile", "component"]),
        ]
        for query, expected in test_cases:
            result = integration._extract_search_terms(query)
            assert result == expected, f"Query '{query}' extracted {result}, expected {expected}"

    def test_no_results_provides_guidance(self, integration):
        """Test that no results message provides helpful guidance."""
        # Query for something that won't exist
        result = integration._get_search_results("nonexistent_xyz_component_12345", 1000)
        assert "Try:" in result or "Suggestions:" in result
        assert "find" in result.lower()
