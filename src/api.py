"""Speech-to-Text Blockifier using Whisper base model.

An audio file is loaded and transcribed to text. All the resultant transcribed test will be
included in a single block.
"""
import logging
import pathlib
from typing import Type, Union

import toml
from steamship import Block, File, SteamshipError
from steamship.app import Response, create_handler
from steamship.base import Task, TaskState
from steamship.base.mime_types import MimeTypes
from steamship.plugin.blockifier import Blockifier, Config
from steamship.plugin.inputs.raw_data_plugin_input import RawDataPluginInput
from steamship.plugin.outputs.block_and_tag_plugin_output import \
    BlockAndTagPluginOutput
from steamship.plugin.service import PluginRequest

from src.whisper.client import WhisperClient


class WhisperBlockifierConfig(Config):
    """Config object containing required configuration parameters to initialize a WhisperBlockifier."""

    banana_dev_api_key: str
    banana_dev_whisper_model_key: str


class WhisperBlockifier(Blockifier):
    """Blockifier that transcribes audio files into blocks.

    Attributes
    ----------
    config : WhisperBlockifierConfig
        The required configuration used to instantiate a whisper-s2t-blockifier
    _logger : logging.Logger
        Used to log information on plugin behavior
    _client : whisper.client.WhisperClient
        Client for backend whisper model
    """

    config: WhisperBlockifierConfig

    SUPPORTED_MIME_TYPES = (
        MimeTypes.MP3,
        MimeTypes.WAV,
        "video/mp4",
        "audio/mp4",
        # todo: determine full set of supported audio formats
        # "audio/webm",
        # "video/webm",
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
        self._logger = logging.getLogger(__name__)
        self._client = WhisperClient(
            api_key=self.config.banana_dev_api_key,
            model_key=self.config.banana_dev_whisper_model_key,
        )

    def config_cls(self) -> Type[Config]:
        """Return the Configuration class."""
        return WhisperBlockifierConfig

    def run(
        self, request: PluginRequest[RawDataPluginInput]
    ) -> Union[Response, Response[BlockAndTagPluginOutput]]:
        """Transcribe the audio file, store the transcription results in blocks and tags."""
        self._logger.info("received request")
        if request.is_status_check:
            return self._check_status(request)

        return self._start_work(request)

    def _check_status(
        self, request: PluginRequest[RawDataPluginInput]
    ) -> Union[Response, Response[BlockAndTagPluginOutput]]:
        if (
            request.status.remote_status_input is None
            or "transcription_id" not in request.status.remote_status_input
        ):
            raise SteamshipError(
                message="Status check requests must provide a valid 'transcription_id'."
            )

        return self._check_transcription_status(
            request.status.remote_status_input.get("transcription_id")
        )

    def _check_transcription_status(
        self, transcription_id: str
    ) -> Union[Response, Response[BlockAndTagPluginOutput]]:
        self._logger.info(f"checking transcription status id={transcription_id}")

        try:
            whisper_response = self._client.check_transcription_request(transcription_id)
            if WhisperClient.is_success(whisper_response):
                self._logger.info(f"transcription complete id={transcription_id}")
                return Response(
                    data=BlockAndTagPluginOutput(
                        file=File.CreateRequest(
                            blocks=[
                                Block.CreateRequest(
                                    text=WhisperClient.get_transcription(whisper_response)
                                )
                            ]
                        )
                    )
                )
        except Exception as e:
            if "error" in str(e).lower():
                self._logger.info(f"transcription failed id={transcription_id}")
                # todo: should we raise an error here, or report a failure through normal mechanisms?
                raise SteamshipError(message=f"Transcription failed: {e!s}")

            self._logger.info(f"could not get status of transcription id={transcription_id}: {e!s}")

        # default to returning an "in-progress" status
        self._logger.info(f"transcription in-progress id={transcription_id}")
        return Response(
            status=Task(
                state=TaskState.running,
                remote_status_message="Transcription job ongoing.",
                remote_status_input={"transcription_id": transcription_id},
            )
        )

    def _start_work(
        self, request: PluginRequest
    ) -> Union[Response, Response[BlockAndTagPluginOutput]]:
        self._check_mime_type(request)
        self._logger.info("starting transcription...")

        try:
            transcription_id = self._client.start_transcription(request.data.data)
        except Exception as e:
            raise SteamshipError(f"could not schedule work: {e!s}")

        return self._check_transcription_status(transcription_id)

    def _check_mime_type(self, request: PluginRequest) -> str:
        mime_type = request.data.default_mime_type
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise SteamshipError(
                "Unsupported mimeType. "
                f"The following mimeTypes are supported: {self.SUPPORTED_MIME_TYPES}"
            )

        return mime_type


handler = create_handler(WhisperBlockifier)
