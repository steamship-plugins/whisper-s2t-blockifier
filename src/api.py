"""Speech-to-Text Blockifier using Whisper base model.

An audio file is loaded and transcribed to text. All the resultant transcribed test will be
included in a single block.
"""
import json
import logging
import pathlib
from typing import Type, Union

import toml
from steamship import SteamshipError
from steamship.base import TaskState
from steamship.base.mime_types import MimeTypes
from steamship.invocable import Config, InvocableResponse, create_handler
from steamship.plugin.blockifier import Blockifier
from steamship.plugin.inputs.raw_data_plugin_input import RawDataPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import BlockAndTagPluginOutput
from steamship.plugin.request import PluginRequest

import block
import steamship_response
import tag
import whisper.response as whisper_response
from whisper.client import WhisperClient


class WhisperBlockifierConfig(Config):
    """Config object containing required configuration parameters to initialize a WhisperBlockifier."""

    banana_dev_api_key: str
    banana_dev_whisper_model_key: str

    # configuration that will be used to select configurable whisper model.
    get_segments: bool
    whisper_model: str


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

    SUPPORTED_MIME_TYPES = (
        # todo: determine full set of supported audio formats (or should we eliminate this check? it feels like a foot-gun.)
        MimeTypes.MP3,
        MimeTypes.WAV,
        MimeTypes.MP4_VIDEO,
        MimeTypes.MP4_AUDIO,
        "audio/webm",
        "video/webm",
        "audio/mp4a-latm",
        "audio/mpeg",
    )

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
        try:
            self._client = WhisperClient(
                api_key=self.config.banana_dev_api_key,
                model_key=self.config.banana_dev_whisper_model_key,
                whisper_model=self.config.whisper_model,
            )
        except ValueError as ve:
            raise SteamshipError(
                message=f"A valid whisper model type must be supplied in configuration: {ve}"
            )

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
        out = self._client.check_transcription_request(transcription_id)
        if whisper_response.is_success(out):
            logging.info(f"transcription complete id={json.dumps(transcription_id)}")
            if self.config.get_segments:
                logging.info(f"getting segments id={json.dumps(transcription_id)}")
                tags = []
                transcription_text = ""
                for segment in whisper_response.get_segments(out):
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
                [block.create_from_text(whisper_response.get_transcription(out))]
            )

        logging.info(f"transcription in-progress id={json.dumps(transcription_id)}")
        return steamship_response.with_status(
            TaskState.running, "Transcription job ongoing.", transcription_id
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
        logging.debug("starting transcription...")

        try:
            transcription_id = self._client.start_transcription(
                request.data.data, self.config.get_segments
            )
            logging.info(f"started transcription: id={json.dumps(transcription_id)}")
        except Exception as e:
            raise SteamshipError(f"could not schedule work: {json.dumps(e)}")

        try:
            return self._check_transcription_status(transcription_id)
        except Exception as exc:
            self._handle_check_error(str(exc), transcription_id)

    def _check_mime_type(self, request: PluginRequest) -> str:
        mime_type = request.data.default_mime_type
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise SteamshipError(
                f"Unsupported mime_type: {mime_type}."
                f"The following mime_types are supported: {self.SUPPORTED_MIME_TYPES}"
            )

        return mime_type


handler = create_handler(WhisperBlockifier)
