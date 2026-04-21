# TTS Plugin Addition Guide

## Architecture

```
tts_engine.py           # Abstract base class TTSEngine
├── tts_edge.py         # edge-tts implementation
├── tts_voicevox.py     # VOICEVOX API implementation
├── tts_elevenlabs.py   # ElevenLabs API implementation (Voice Clone support)
├── tts_openai.py       # OpenAI TTS API implementation (compatible-server support)
└── tts_xxx.py          # New plugin (added by you)
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
    choices=["edge", "voicevox", "elevenlabs", "openai", "xxx"],
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

### ElevenLabs
- **Dependency**: `httpx` package
- **Environment variables**: `ELEVENLABS_API_KEY` (required), `ELEVENLABS_API_BASE` (optional)
- **Features**: High-quality cloud TTS. Pass your own Voice Clone `voice_id` via `--voice`.
- **Default voice**: Rachel (`21m00Tcm4TlvDq8ikWAM`)
- **Default model**: `eleven_multilingual_v2`

### OpenAI
- **Dependency**: `httpx` package
- **Environment variables**: `OPENAI_API_KEY` (required), `OPENAI_API_BASE` (optional, for compatible servers), `OPENAI_TTS_MODEL` (optional)
- **Features**: Official OpenAI TTS only supports preset voices (e.g., `alloy`). When using OpenAI-compatible servers, pass the custom voice name via `--voice`.
- **Default voice**: `alloy`
- **Default model**: `tts-1`

---

## API key / environment variable setup (user-facing)

Cloud TTS engines (ElevenLabs / OpenAI) read API keys from environment
variables. Do not hard-code keys in CLI arguments or source files.

### Recognized environment variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key | When using ElevenLabs |
| `ELEVENLABS_API_BASE` | Override API base URL (proxy, etc.) | Optional |
| `OPENAI_API_KEY` | OpenAI API key | When using OpenAI |
| `OPENAI_API_BASE` | Override API base URL (compatible servers) | Optional |
| `OPENAI_TTS_MODEL` | Override model name (e.g., `tts-1-hd`) | Optional |

### Setup options (pick one)

#### A. Current shell session only

```bash
export ELEVENLABS_API_KEY="sk_..."
export OPENAI_API_KEY="sk-..."
```

Lost when the terminal closes. Useful for quick tests.

#### B. Persist (recommended)

Append to `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export ELEVENLABS_API_KEY="sk_..."' >> ~/.bashrc
source ~/.bashrc
```

#### C. `.env` file

Create `.env` in the project directory:

```
ELEVENLABS_API_KEY=sk_...
OPENAI_API_KEY=sk-...
```

Load before running (assumes `.env` is in `.gitignore`):

```bash
set -a && source .env && set +a
```

### Getting an API key

- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys → "Create API Key"
- **OpenAI**: https://platform.openai.com/api-keys → "Create new secret key"

### Verify the setup

```bash
# Check presence only — never echo the value to logs / transcripts.
test -n "${ELEVENLABS_API_KEY:-}" && echo "ELEVENLABS_API_KEY: set"
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY: set"
```

### Find your Voice Clone `voice_id` (ElevenLabs)

1. Open https://elevenlabs.io/app/voice-lab
2. Select your Voice Clone
3. Copy the displayed voice_id (e.g., `21m00Tcm4TlvDq8ikWAM`)
4. Pass via `--voice <voice_id>`

### Security notes

- Never paste API keys into chat history or commits. Share only the variable
  *name* (e.g., `ELEVENLABS_API_KEY`) with Claude Code — never the value.
- If using `.env`, ensure `.env` is in `.gitignore`.
- If you suspect a leak, revoke the key immediately from the provider's dashboard.
