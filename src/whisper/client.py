"""Provides a thin client for a backend running a Whisper model."""

import base64
from typing import Any

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
        """
        encoded = base64.b64encode(raw_audio).decode("ISO-8859-1")
        model_payload = {"mp3BytesString": encoded}
        return banana_dev.start(self._api_key, self._model_key, model_payload)

    def check_transcription_request(self, transcription_id: str) -> dict[str, Any]:
        """Check on the status of an ongoing transcription.

        :param transcription_id: the transcription request identifier that was returned from `start_transcription`
        :return: the structured response from the backend. for details, see https://www.banana.dev/docs/rest-api
        """
        return banana_dev.check(self._api_key, transcription_id)

    @staticmethod
    def get_transcription(response: dict[str, Any]) -> str:
        """Extract the transcribed text from the backend response.

        :param response: the response from `check_transcription_request()`
        :return: the transcribed text, if any
        """
        model_outputs = response.get("modelOutputs") or {}
        return model_outputs.get("text") or ""

    @staticmethod
    def is_error(response: dict[str, Any]) -> bool:
        """Determine if an error was encountered during transcription.

        :param response: the response from `check_transcription_request()`
        :return: true, if there was an error; false otherwise.
        """
        # https://www.banana.dev/docs/rest-api: if message contains "error", then the inference failed.
        message = response["message"]
        return "error" in message

    @staticmethod
    def is_success(response: dict[str, Any]) -> bool:
        """Determine if the backend has indicated the transcription completed successfully.

        :param response: the response from `check_transcription_request()`
        :return: true, if transcription was successful; false otherwise.
        """
        # https://www.banana.dev/docs/rest-api: if message == "success", then the results will be found in the
        # modelOutputs field.
        message = response["message"]
        return message == "success"
