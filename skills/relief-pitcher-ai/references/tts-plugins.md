# TTS Plugin Addition Guide

## Architecture

```
tts_engine.py       # Abstract base class TTSEngine
├── tts_edge.py     # edge-tts implementation
├── tts_voicevox.py # VOICEVOX API implementation
└── tts_xxx.py      # New plugin (added by you)
```

## Steps to Add a New TTS Plugin

### 1. Create the implementation class

`daida_ai/lib/tts_xxx.py`:

```python
from daida_ai.lib.tts_engine import TTSEngine
from pathlib import Path

class XxxTTSEngine(TTSEngine):
    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        # Speech synthesis logic
        # Write the audio file to output_path
        return output_path

    def available_voices(self) -> list[str]:
        return ["voice1", "voice2"]
```

### 2. Register in the factory function

Add a branch to `get_engine()` in `daida_ai/lib/tts_engine.py`:

```python
elif name == "xxx":
    from daida_ai.lib.tts_xxx import XxxTTSEngine
    return XxxTTSEngine()
```

### 3. Write tests

`tests/test_tts_xxx.py`:
- Does `synthesize()` successfully generate a file?
- Does `available_voices()` return a non-empty list?
- Error handling (e.g., API down)

### 4. Update the CLI script

Add to the `--engine` choices in `synthesize_audio.py`:

```python
parser.add_argument(
    "--engine",
    choices=["edge", "voicevox", "xxx"],
    ...
)
```

## Current Plugins

### edge-tts (default)
- **Dependency**: `edge-tts` package
- **Features**: Free, requires internet connection, high-quality Japanese voices
- **Default voice**: `ja-JP-NanamiNeural`

### VOICEVOX
- **Dependency**: `httpx` package, VOICEVOX Engine (localhost:50021)
- **Features**: Local execution, character voices, emotion parameter support
- **Default voice**: Speaker ID 1 (Zundamon)
