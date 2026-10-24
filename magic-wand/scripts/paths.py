"""Canonical source and publication roots; independent of the caller's working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parent
DOCS = REPOSITORY / "docs"

def resolve_artifact(relative: str) -> Path:
    """Manifest source paths are component-relative; published docs paths are repo-relative."""
    return (REPOSITORY if relative.startswith("docs/") else ROOT) / relative
