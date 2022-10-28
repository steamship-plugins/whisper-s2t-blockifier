"""Utility methods for generating Responses."""

from typing import List

from steamship import Block, File
from steamship.base import Task, TaskState
from steamship.invocable import InvocableResponse
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput


def with_blocks(blocks: List[Block.CreateRequest]) -> InvocableResponse[BlockAndTagPluginOutput]:
    """Build a block-and-tag response from text."""
    return InvocableResponse(data=BlockAndTagPluginOutput(file=File.CreateRequest(blocks=blocks)))


def with_status(state: TaskState, message, transcription_id: str) -> InvocableResponse:
    """Build a response object with a TaskState and message for a given transcription_id."""
    return InvocableResponse(
        status=Task(
            state=state,
            remote_status_message=message,
            remote_status_input={"transcription_id": transcription_id},
        )
    )
