"""Provides a thin client for a backend running a Whisper model."""

import base64
from typing import Any, Dict

import banana_dev


class WhisperClient:
    """
    A thin wrapper around a backend that provides a callable Whisper model that can be used for transcription.

    The current implementation uses a banana.dev backend. This client wraps the banana_dev SDK to allow ease of
    use within a Steamship plugin (and during testing).

    Attributes
    ----------
    _api_key : str
      the API key to use for the backend
    _model_key : str
      the key used to identify the model in the backend
    """

    def __init__(self, api_key, model_key: str):
        """Initialize client with appropriate keys."""
        self._api_key = api_key
        self._model_key = model_key

    def start_transcription(self, raw_audio: bytes) -> str:
        """Request transcription of the supplied audio file.

        :param raw_audio: the audio file bytes (unencoded)
        :return: a transcription request identifier. this will be used to check on transcription status.
        :raises Exception: when errors communicating with the backend model are encountered. This includes successful
        requests that have "error" in a "message" field in their returned struct.
        """
        encoded = base64.b64encode(raw_audio).decode("ISO-8859-1")
        model_payload = {"mp3BytesString": encoded}
        return banana_dev.start(self._api_key, self._model_key, model_payload)

    def check_transcription_request(self, transcription_id: str) -> Dict[str, Any]:
        """Check on the status of an ongoing transcription.

        :param transcription_id: the transcription request identifier that was returned from `start_transcription`
        :return: the structured response from the backend. for details, see https://www.banana.dev/docs/rest-api
        :raises Exception: when errors communicating with the backend model are encountered. This includes successful
        requests that have "error" in a "message" field in their returned struct.
        """
        return banana_dev.check(self._api_key, transcription_id)
