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
from steamship import Steamship, PluginInstance, File, MimeTypes

PLUGIN_HANDLE = "whisper-s2t-blockifier"
PLUGIN_CONFIG = {}

client = Steamship(profile="staging")  # Without arguments, credentials in ~/.steamship.json will be used.
s2t_plugin_instance = PluginInstance.create(
    client, plugin_handle=PLUGIN_HANDLE, config=PLUGIN_CONFIG
).data
audio_path = "FILL_IN"
file = File.create(client, filename=str(audio_path.resolve()), mime_type=MimeTypes.MP3).data
tag_results = file.tag(plugin_instance=s2t_plugin_instance.handle)
tag_results.wait()

file = file.refresh().data
for block in file.blocks:
    print(block.text)
```

## Developing

Development instructions are located in [DEVELOPING.md](DEVELOPING.md)

## Testing

Testing instructions are located in [TESTING.md](TESTING.md)

## Deploying

Deployment instructions are located in [DEPLOYING.md](DEPLOYING.md)
