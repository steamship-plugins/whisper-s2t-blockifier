"""Utility methods for creating blocks."""
from typing import List, Optional

from steamship import Block, Tag


def create_from_text(
    transcription: str, tags: Optional[List[Tag.CreateRequest]] = None
) -> Block.CreateRequest:
    """Build a block from a chunk of text and (optionally) some tags."""
    if tags is None:
        tags = []
    return Block.CreateRequest(text=transcription, tags=tags)
