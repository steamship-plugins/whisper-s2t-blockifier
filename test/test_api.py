"""Unit tests for the whisper-s2t-blockifier."""

from typing import Any, Dict

import pytest
from steamship import Block, File, SteamshipError
from steamship.base import Task, TaskState
from steamship.invocable import InvocableResponse
from steamship.plugin.inputs.raw_data_plugin_input import RawDataPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput
from steamship.plugin.request import PluginRequest

from api import WhisperBlockifier, tag

NEW_TRANSCRIPTION_ID = "foo-new1234"
NEW_TRANSCRIPTION_REQUEST = PluginRequest[RawDataPluginInput]()
NEW_TRANSCRIPTION_REQUEST.data = RawDataPluginInput(data="", defaultMimeType="audio/wav")
NEW_TRANSCRIPTION_REQUEST.is_status_check = False
NEW_TRANSCRIPTION_RESPONSE = InvocableResponse(
    Task(
        state=TaskState.running,
        remote_status_message="Transcription job ongoing.",
        remote_status_input={"transcription_id": NEW_TRANSCRIPTION_ID},
    )
)

INVALID_TRANSCRIPTION_ID = "foo-invalid1234"
INVALID_TRANSCRIPTION_REQUEST = PluginRequest[RawDataPluginInput]()
INVALID_TRANSCRIPTION_REQUEST.data = RawDataPluginInput(
    data="", defaultMimeType="no-audio/in-any-way"
)
INVALID_TRANSCRIPTION_REQUEST.is_status_check = False

RUNNING_TRANSCRIPTION_ID = "running-1234"
STATUS_RUNNING = Task(
    state=TaskState.running,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": RUNNING_TRANSCRIPTION_ID},
)
RUNNING_REQUEST = PluginRequest[RawDataPluginInput]()
RUNNING_REQUEST.is_status_check = True
RUNNING_REQUEST.status = STATUS_RUNNING
RUNNING_RESPONSE = InvocableResponse(status=STATUS_RUNNING)

STATUS_MISSING_TRANSCRIPTION_ID = Task(state=TaskState.running)
MISSING_REQUEST = PluginRequest[RawDataPluginInput]()
MISSING_REQUEST.is_status_check = True
MISSING_REQUEST.status = STATUS_MISSING_TRANSCRIPTION_ID

ERROR_TRANSCRIPTION_ID = "error-1234"
STATUS_ERROR = Task(
    state=TaskState.running,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": ERROR_TRANSCRIPTION_ID},
)
ERROR_REQUEST = PluginRequest[RawDataPluginInput]()
ERROR_REQUEST.is_status_check = True
ERROR_REQUEST.status = STATUS_ERROR

COMPLETE_TRANSCRIPTION_ID = "complete-1234"
STATUS_CHECK_COMPLETE = Task(
    state=TaskState.running,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": COMPLETE_TRANSCRIPTION_ID},
)
COMPLETE_REQUEST = PluginRequest[RawDataPluginInput]()
COMPLETE_REQUEST.is_status_check = True
COMPLETE_REQUEST.status = STATUS_CHECK_COMPLETE
STATUS_COMPLETE = Task(
    state=TaskState.succeeded,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": COMPLETE_TRANSCRIPTION_ID},
)
COMPLETE_RESPONSE = InvocableResponse(
    data=BlockAndTagPluginOutput(
        file=File.CreateRequest(blocks=[Block.CreateRequest(text="why, hello there!")])
    )
)

COMPLETE_SEGMENTS_ID = "complete-segments-1234"
STATUS_CHECK_SEGMENTS_COMPLETE = Task(
    state=TaskState.running,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": COMPLETE_SEGMENTS_ID},
)
COMPLETE_SEGMENTS_REQUEST = PluginRequest[RawDataPluginInput]()
COMPLETE_SEGMENTS_REQUEST.is_status_check = True
COMPLETE_SEGMENTS_REQUEST.status = STATUS_CHECK_SEGMENTS_COMPLETE
STATUS_SEGMENTS_COMPLETE = Task(
    state=TaskState.succeeded,
    remote_status_message="Transcription job ongoing.",
    remote_status_input={"transcription_id": COMPLETE_SEGMENTS_ID},
)
COMPLETE_SEGMENTS_RESPONSE = InvocableResponse(
    data=BlockAndTagPluginOutput(
        file=File.CreateRequest(
            blocks=[
                Block.CreateRequest(
                    text="why, hello there!",
                    tags=[
                        tag.create_timestamp(0, 1.034, 2.30, "why, hello"),
                        tag.create_timestamp(11, 2.30, 4.0345, "there!"),
                    ],
                )
            ]
        )
    )
)


class MockWhisperClient:
    """Mock client used exclusively for testing."""

    ids_to_responses = {
        NEW_TRANSCRIPTION_ID: {"message": "transcription is running"},
        RUNNING_TRANSCRIPTION_ID: {"message": "transcription is running"},
        COMPLETE_TRANSCRIPTION_ID: {
            "message": "success",
            "modelOutputs": [{"text": "why, hello there!"}],
        },
        COMPLETE_SEGMENTS_ID: {
            "message": "success",
            "modelOutputs": [
                {
                    "segments": [
                        {"start": 1.034, "end": 2.30, "text": "why, hello"},
                        {"start": 2.30, "end": 4.0345, "text": "there!"},
                    ]
                }
            ],
        },
    }

    def start_transcription(self, audio_url: str) -> Dict[str, Any]:
        """Mock method."""
        return {"callID": NEW_TRANSCRIPTION_ID}

    def check_transcription_request(self, transcription_id: str) -> Dict[str, Any]:
        """Mock method."""
        if transcription_id == ERROR_TRANSCRIPTION_ID:
            raise Exception("ERROR: unknown words")

        return self.ids_to_responses.get(transcription_id)


testdata = [
    (
        NEW_TRANSCRIPTION_REQUEST,
        NEW_TRANSCRIPTION_RESPONSE,
        False,
        False,
    ),  # full transcription, no exception expected
    (
        INVALID_TRANSCRIPTION_REQUEST,
        None,
        False,
        True,
    ),  # full transcription, expect exception
    (
        RUNNING_REQUEST,
        RUNNING_RESPONSE,
        False,
        False,
    ),  # full transcription, no exception expected
    (ERROR_REQUEST, None, False, True),  # full transcription, expect exception
    (MISSING_REQUEST, None, False, True),  # full transcription, expect exception
    (
        COMPLETE_REQUEST,
        COMPLETE_RESPONSE,
        False,
        False,
    ),  # full transcription, no exception expected
    (
        COMPLETE_SEGMENTS_REQUEST,
        COMPLETE_SEGMENTS_RESPONSE,
        True,
        False,
    ),  # segments, no exception expected
]


@pytest.mark.parametrize(
    "plugin_request, expected_response, use_meeting_transcription_model, want_exception",
    testdata,
    ids=[
        "new_transcription",
        "invalid_transcription",
        "running_transcription",
        "error_transcription",
        "missing_transcription_id",
        "completed_transcription",
        "completed_segments",
    ],
)
def test_run(
    plugin_request, expected_response, use_meeting_transcription_model, want_exception, mocker
):
    """Tests the run() method of the blockifier, using a mock backend client."""
    blockifier = WhisperBlockifier(
        config={"use_meeting_transcription_model": use_meeting_transcription_model}
    )
    mocker.patch.object(blockifier, "_client", MockWhisperClient())
    mocker.patch.object(
        blockifier, "_get_public_url_for_audio", return_value="https://fake/audio.m4a"
    )

    try:
        got_response = blockifier.run(plugin_request)
        assert want_exception is False, "run() should have resulted in a raised SteamshipError"
        assert got_response == expected_response, "run() produced incorrect results"
    except SteamshipError as e:
        assert want_exception is True, f"run() produced unexpected exception: {str(e)}"
