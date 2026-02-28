"""Pytest configuration."""
import sys
from pathlib import Path

# Ensure project root is importable regardless of where pytest is invoked
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
