"""Enumerate suite files without local environments or generated artifacts."""
import os
from pathlib import Path


def source_files(root):
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "artifacts", "dist", "build"}
    for directory, children, files in os.walk(root):
        children[:] = sorted(name for name in children if name not in ignored)
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix != ".pyc" and path.is_file():
                yield path
