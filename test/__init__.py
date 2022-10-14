"""Testing suite including integration and unit tests."""
from pathlib import Path

TEST_DATA = Path(__file__).parent / "data"
REPO_ROOTDIR = Path(__file__).parent.parent
DOT_STEAMSHIP = REPO_ROOTDIR / "src" / ".steamship"
