"""Speech-to-Text Blockifier using Whisper base model.

An audio file is loaded and transcribed to text. All the resultant transcribed test will be
included in a single block.
"""
import json
import logging
import pathlib
import uuid
from typing import Any, Dict, Type, Union

import toml
from steamship import SteamshipError
from steamship.base import TaskState
from steamship.data.workspace import SignedUrl
from steamship.invocable import Config, InvocableResponse
from steamship.plugin.blockifier import Blockifier
from steamship.plugin.inputs.raw_data_plugin_input import RawDataPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput
from steamship.plugin.request import PluginRequest
from steamship.utils.signed_urls import upload_to_signed_url

import block
import steamship_response
import tag
import whisper.response as whisper_response
from whisper.client import WhisperClient


class WhisperBlockifierConfig(Config):
    """Config object containing required configuration parameters to initialize a WhisperBlockifier."""

    banana_dev_api_key: str
    banana_dev_base_whisper_model_key: str
    banana_dev_meeting_transcription_whisper_model_key: str

    use_meeting_transcription_model: bool


class WhisperBlockifier(Blockifier):
    """Blockifier that transcribes audio files into blocks.

    Attributes
    ----------
    config : WhisperBlockifierConfig
        The required configuration used to instantiate a whisper-s2t-blockifier
    _client : whisper.client.WhisperClient
        Client for backend whisper model
    """

    config: WhisperBlockifierConfig

    def __init__(self, **kwargs):
        """Initialize Blockifier."""
        # todo: handle load errors?
        secret_kwargs = toml.load(
            str(pathlib.Path(__file__).parent / ".steamship" / "secrets.toml")
        )
        config = kwargs.get("config") or {}
        kwargs["config"] = {
            **secret_kwargs,
            **{k: v for k, v in config.items() if v != ""},
        }

        super().__init__(**kwargs)

        model_key = self.config.banana_dev_base_whisper_model_key
        if self.config.use_meeting_transcription_model:
            model_key = self.config.banana_dev_meeting_transcription_whisper_model_key

        self._client = WhisperClient(api_key=self.config.banana_dev_api_key, model_key=model_key)

    def config_cls(self) -> Type[Config]:
        """Return the Configuration class."""
        return WhisperBlockifierConfig

    def run(
        self, request: PluginRequest[RawDataPluginInput]
    ) -> Union[InvocableResponse, InvocableResponse[BlockAndTagPluginOutput]]:
        """Transcribe the audio file, store the transcription results in blocks and tag.py."""
        logging.debug("received request")
        if request.is_status_check:
            return self._check_status(request)

        return self._start_work(request)

    def _check_status(
        self, request: PluginRequest[RawDataPluginInput]
    ) -> Union[InvocableResponse, InvocableResponse[BlockAndTagPluginOutput]]:
        if (
            request.status.remote_status_input is None
            or "transcription_id" not in request.status.remote_status_input
        ):
            raise SteamshipError(
                message="Status check requests must provide a valid 'transcription_id'."
            )

        transcription_id = request.status.remote_status_input.get("transcription_id")
        try:
            return self._check_transcription_status(transcription_id)
        except Exception as exc:
            self._handle_check_error(str(exc), transcription_id)

    def _check_transcription_status(
        self, transcription_id: str
    ) -> Union[InvocableResponse, InvocableResponse[BlockAndTagPluginOutput]]:
        logging.info(f"checking transcription status id={json.dumps(transcription_id)}")
        response_json = self._client.check_transcription_request(transcription_id)
        return self._check_model_output(response_json, transcription_id)

    def _check_model_output(
        self, response_json: Dict[str, Any], transcription_id: str
    ) -> Union[InvocableResponse, InvocableResponse[BlockAndTagPluginOutput]]:
        if not whisper_response.is_success(response_json) and not whisper_response.is_finished(
            response_json
        ):
            logging.info(f"transcription in-progress id={json.dumps(transcription_id)}")
            return steamship_response.with_status(
                TaskState.running, "Transcription job ongoing.", transcription_id
            )

        logging.info(f"transcription complete id={json.dumps(transcription_id)}")
        if self.config.use_meeting_transcription_model:
            logging.info(f"getting segments id={json.dumps(transcription_id)}")
            tags = []
            transcription_text = ""
            for segment in whisper_response.get_segments(response_json):
                segment_text = segment["text"].strip()
                transcription_text = f"{transcription_text} {segment_text}".strip()
                tags.append(
                    tag.create_timestamp(
                        len(transcription_text) - len(segment_text),
                        segment["start"],
                        segment["end"],
                        segment_text,
                    )
                )
            logging.info(f"returning blocks with tags: {len(tags)}")
            return steamship_response.with_blocks(
                [block.create_from_text(transcription_text, tags)]
            )

        logging.info("returning blocks without tags")
        return steamship_response.with_blocks(
            [block.create_from_text(whisper_response.get_transcription(response_json))]
        )

    def _handle_check_error(self, message, transcription_id: str) -> InvocableResponse:
        msg = message.lower()
        if msg.startswith("server error:"):
            logging.warning(
                f"could not get status of transcription id={json.dumps(transcription_id)} error={json.dumps(msg)}"
            )
            return steamship_response.with_status(
                TaskState.running, "Transcription job ongoing.", transcription_id
            )

        logging.error(
            f"transcription failed id={json.dumps(transcription_id)} error={json.dumps(msg)}"
        )
        raise SteamshipError(message=f"Transcription failed: {json.dumps(msg)}")

    def _start_work(
        self, request: PluginRequest
    ) -> Union[InvocableResponse, InvocableResponse[BlockAndTagPluginOutput]]:
        self._check_mime_type(request)

        read_url = self._get_public_url_for_audio(request)
        logging.info(f"starting transcription for {read_url}...")

        try:
            response_json = self._client.start_transcription(read_url)
            logging.error(f"response: {response_json}")
            task_id = WhisperClient.task_identifier(response_json)
            if len(task_id) == 0:
                task_id = "task-completed"
            logging.info(f"started transcription: id={json.dumps(task_id)}")
            return self._check_model_output(response_json, task_id)
        except Exception as e:
            raise SteamshipError(f"could not schedule work: {json.dumps(e)}")

    def _get_public_url_for_audio(self, request):
        logging.debug("creating signed URL...")
        filepath = str(uuid.uuid4())
        signed_url = (
            self.client.get_workspace()
            .create_signed_url(
                SignedUrl.Request(
                    bucket=SignedUrl.Bucket.PLUGIN_DATA,
                    filepath=filepath,
                    operation=SignedUrl.Operation.WRITE,
                )
            )
            .signed_url
        )
        logging.debug(f"uploading to signed url: {signed_url}...")
        upload_to_signed_url(signed_url, request.data.data)
        read_url = (
            self.client.get_workspace()
            .create_signed_url(
                SignedUrl.Request(
                    bucket=SignedUrl.Bucket.PLUGIN_DATA,
                    filepath=filepath,
                    operation=SignedUrl.Operation.READ,
                )
            )
            .signed_url
        )
        return read_url

    def _check_mime_type(self, request: PluginRequest) -> str:
        mime_type = request.data.default_mime_type
        if not (mime_type.startswith("audio/") or mime_type.startswith("video/")):
            raise SteamshipError(
                f"Unsupported mime_type: {mime_type}."
                f"Only audio/* and video/* mime types are supported."
            )

        return mime_type
