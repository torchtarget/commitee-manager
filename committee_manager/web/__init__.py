"""Simple Flask-based web interface for committee allocation."""
from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
