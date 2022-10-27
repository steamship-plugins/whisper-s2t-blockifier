"""Utility methods for handling the whisper client response."""

from typing import Any, Dict, List


def get_transcription(response: Dict[str, Any]) -> str:
    """Extract the transcribed text from the backend response, if it exists.

    :param response: the response from `check_transcription_request()`
    :return: the transcribed text, if any
    """
    model_outputs = response.get("modelOutputs") or []
    if len(model_outputs) < 1:
        return ""

    return model_outputs[0].get("text").strip() or ""


def get_segments(response: Dict[str, Any]) -> List[Any]:
    """Extract the transcriptions of audio segments from the backend response, if they exist.

    :param response: the response from `check_transcription_request()`
    :return: the segments, including start, end, and text, if any exist
    """
    model_outputs = response.get("modelOutputs") or []
    if len(model_outputs) < 1:
        return []

    return model_outputs[0].get("segments", [])


def is_success(response: Dict[str, Any]) -> bool:
    """Determine if the backend has indicated the transcription completed successfully.

    :param response: the response from `check_transcription_request()`
    :return: true, if transcription was successful; false otherwise.
    """
    # https://www.banana.dev/docs/rest-api: if message == "success", then the results will be found in the
    # modelOutputs field.
    message = response["message"].lower()
    return message == "success"
