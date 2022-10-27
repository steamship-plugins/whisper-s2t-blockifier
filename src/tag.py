"""Utility methods for creating tags."""
from steamship import Tag


def create_timestamp(
    start_idx: int, start_offset_seconds, end_offset_seconds: float, text: str
) -> Tag.CreateRequest:
    """Create a Tag with a kind of 'timestamp' for the text provided."""
    # todo(douglas-reid): should we use `name` to hold the text, or also add it to `value` ?
    return Tag.CreateRequest(
        kind="timestamp",
        start_idx=start_idx,
        end_idx=start_idx + len(text),
        name=text,
        value={"start_time": start_offset_seconds, "end_time": end_offset_seconds},
    )
