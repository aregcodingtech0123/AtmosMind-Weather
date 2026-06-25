"""Tests for SQLite helper security and query behavior."""
from __future__ import annotations

from database import escape_like_pattern


def test_escape_like_pattern_treats_percent_and_underscore_as_literals():
    assert escape_like_pattern("100%") == "100\\%"
    assert escape_like_pattern("new_york") == "new\\_york"
    assert escape_like_pattern("a\\b") == "a\\\\b"
