# Whisper Transcribe blockifier

This project contains a Steamship Blockifier that transcribes audio files via Whisper.

## Configuration

This plugin is configured using an API key and a model key for the backend that is running the Whisper model. Those keys
are supplied via secrets.

## Getting Started

### Usage

To authenticate with Steamship, install the Steamship CLI with:

```bash
> npm install -g @steamship/cli
```

And then login with:

```bash
> ship login
```

```python
from steamship import Steamship, File, MimeTypes

workspace = Steamship(workspace="whisper-s2t-plugin-demo-001")
plugin_config = {"get_segments": True, "whisper_model": "tiny"}
whisper = workspace.use_plugin("whisper-s2t-blockifier-staging", "whisper-instance-0001", config=plugin_config)

audio_path = "FILL_IN"
file = File.create(whisper.client, content=audio_path.open('rb').read(), mime_type=MimeTypes.MP3)
blockify_response = file.blockify(plugin_instance=whisper.handle)
blockify_response.wait(max_timeout_s=3600, retry_delay_s=1)

file = file.refresh()

for block in file.blocks:
    print(block.text)
```

## Developing

Development instructions are located in [DEVELOPING.md](DEVELOPING.md)

## Testing

Testing instructions are located in [TESTING.md](TESTING.md)

## Deploying

Deployment instructions are located in [DEPLOYING.md](DEPLOYING.md)
