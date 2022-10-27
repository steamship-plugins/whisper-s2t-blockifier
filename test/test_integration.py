"""Test whisper-s2t-blockifier via integration tests."""
import json
from test import REPO_ROOTDIR, TEST_DATA
from typing import Any, Dict

from steamship import File, PluginInstance, Steamship
from steamship.base.mime_types import MimeTypes

ENVIRONMENT = "staging"


def _get_plugin_instance(client: Steamship, config: Dict[str, Any] = None) -> PluginInstance:
    steamship_manifest = json.load(open(REPO_ROOTDIR / "steamship.json", "rb"))
    plugin_handle = steamship_manifest.get("handle") or ""
    plugin_version_handle = steamship_manifest.get("version") or ""
    plugin_instance = PluginInstance.create(
        client,
        plugin_handle=plugin_handle,
        plugin_version_handle=plugin_version_handle,
        upsert=True,
        config=config,
    ).data
    assert plugin_instance is not None
    assert plugin_instance.id is not None
    return plugin_instance


def test_blockifier():
    """Test the Whisper Blockifier via an integration test."""
    client = Steamship(profile=ENVIRONMENT)
    config = {"model": "tiny", "get_segments": False}
    blockifier = _get_plugin_instance(client=client, config=config)
    audio_path = TEST_DATA / "OSR_us_000_0010_8k.wav"
    file = File.create(client, filename=str(audio_path.resolve()), mime_type=MimeTypes.WAV).data

    blockify_response = file.blockify(plugin_instance=blockifier.handle)
    blockify_response.wait(max_timeout_s=3600, retry_delay_s=0.1)

    file = file.refresh().data
    verify_file(file)


def verify_file(file) -> None:
    """Verify the blockified file."""
    assert len(file.tags) == 0
    assert file.blocks is not None
    assert len(file.blocks) == 1
    assert file.blocks[0] is not None
    block = file.blocks[0]
    assert block.text is not None

    transcription_path = TEST_DATA / "transcription.txt"
    want_text = open(transcription_path).read()
    assert block.text == want_text
