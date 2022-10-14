"""Utility methods for creating blocks."""

from steamship import Block


def create_from_text(transcription: str) -> Block.CreateRequest:
    """Build a block from a chunk of text."""
    return Block.CreateRequest(
        text=transcription
    )
