"""Utility methods for generating Responses."""

from typing import List

from steamship import Block, File
from steamship.app import Response
from steamship.base import Task, TaskState
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput


def with_blocks(blocks: List[Block.CreateRequest]) -> Response[BlockAndTagPluginOutput]:
    """Build a block-and-tag response from text."""
    return Response(data=BlockAndTagPluginOutput(file=File.CreateRequest(blocks=blocks)))


def with_status(state: TaskState, message, transcription_id: str) -> Response:
    """Build a response object with a TaskState and message for a given transcription_id."""
    return Response(
        status=Task(
            state=state,
            remote_status_message=message,
            remote_status_input={"transcription_id": transcription_id},
        )
    )
