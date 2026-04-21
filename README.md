[English](./README.md) | [日本語](./README_JA.md) | [简体中文](./README_ZH.md) | [한국어](./README_KO.md)

# Relief Pitcher AI

A Claude Code Plugin that auto-generates presentation materials — so AI can pitch in your place.

> **daida-ai** (from Japanese *daida* 代打 — pinch hitter): just as a relief pitcher steps onto the mound when you can't, this plugin takes over and delivers your entire presentation for you.

## Features

1. Input a talk theme and generate a structured outline in Markdown
2. Build slide decks from the outline
   - Slides are generated in PowerPoint format
   - Pre-designed slide templates (dark tech, warm casual, formal business)
   - Slides use proper layouts (not blank canvases) for consistent formatting
   - Titles and body text are set in outline-accessible placeholders
3. Write talk scripts (speaker notes) for each slide
   - Multiple speaking styles: casual, keynote, formal, humorous
4. Synthesize narration audio from the talk scripts
   - Pronunciation dictionary auto-corrects common TTS misreadings
   - TTS scripts can be exported for manual editing
5. Embed synthesized audio into the slides
6. Configure automatic slideshow playback

## Supported Formats

PPTX and ODP (Open Document Presentation)

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3.11+

### Step 1: Add the marketplace

In Claude Code, run:

```
/plugin marketplace add hawkymisc/daida-ai
```

### Step 2: Install the plugin

```
/plugin install daida-ai@hawkymisc-daida-ai
```

### Step 3: Setup

On first use, run `/daida-ai:relief-pitcher-ai` and you will be prompted to execute the setup script.
Follow Claude's instructions and approve:

```bash
bash <plugin-dir>/skills/relief-pitcher-ai/scripts/setup.sh
```

This creates a Python virtual environment and installs all dependencies.

## Usage

Invoke in Claude Code:

```
/daida-ai:relief-pitcher-ai
```

Or use natural language:

- "Create LT slides for me"
- "Generate a presentation"
- "Make a pitch deck"

### Workflow

You'll be asked interactively:

1. **Theme**: What the talk is about
2. **Audience**: Who the talk is for
3. **Duration**: How many minutes (default: 5)
4. **Template**: `tech` / `casual` / `formal`
5. **TTS Engine**: `edge` (default) / `voicevox` / `elevenlabs` / `openai`

The full pipeline runs automatically: Outline → Slides → Talk Script → Audio Synthesis → Audio Embedding → Slideshow Setup.

### Help

Ask "help", "show usage", or "how does this work?" to see the full pipeline diagram.

### Restarting from a Step

If you modify the PPTX or TTS scripts midway, you can say "restart from Step 4" to resume from that step.

Common examples:
- After editing the PPTX manually → "restart from Step 4" to regenerate audio
- After fixing pronunciation → "restart from Step 4c" to re-run audio synthesis only
- To change the template → "restart from Step 2" to regenerate slides

### Fixing TTS Pronunciation

If TTS produces incorrect readings, you can fix them in two ways:

- **Pronunciation dictionary**: Define substitution rules in `skills/relief-pitcher-ai/assets/pronunciation_dict.tsv` (applied automatically at export time)
- **Manual editing**: Export the TTS script and edit it directly in a text editor

## Templates

| Template | Style | Font |
|----------|-------|------|
| `tech` | Dark theme, cyan accents | Noto Sans CJK JP |
| `casual` | Warm tones, rounded design | Noto Sans CJK JP |
| `formal` | White base, business-oriented | Noto Serif CJK JP / Noto Sans CJK JP |

> **Note**: Templates are currently optimized for Japanese content. For other languages, system fonts will be used as fallback.

## TTS Engines

| Engine | Description | Notes |
|--------|-------------|-------|
| edge-tts | Microsoft Edge TTS. No installation required. Supports multiple languages. | Default |
| VOICEVOX | Character voices (e.g., Zundamon). Japanese-language TTS engine. | Requires [VOICEVOX Engine](https://voicevox.hiroshiba.jp/) running |
| ElevenLabs | High-quality cloud TTS with Voice Clone support. Pass your cloned `voice_id` via `--voice`. | Requires `ELEVENLABS_API_KEY` env var |
| OpenAI | OpenAI Text-to-Speech (`tts-1` / `tts-1-hd`). Also works with OpenAI-compatible servers that host custom voice clones. | Requires `OPENAI_API_KEY` env var |

### Using Voice Clones

- **ElevenLabs**: Pass your cloned voice's `voice_id` through `--voice` (e.g., `--engine elevenlabs --voice 21m00Tcm4TlvDq8ikWAM`).
- **OpenAI-compatible servers**: Set `OPENAI_API_BASE` to your server's endpoint, then pass your custom voice name via `--voice`.

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `ELEVENLABS_API_BASE` | ElevenLabs API base URL (optional; defaults to the official endpoint) |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_API_BASE` | OpenAI API base URL (optional; set for OpenAI-compatible servers) |
| `OPENAI_TTS_MODEL` | OpenAI TTS model name (optional; defaults to `tts-1`) |

## Validation

The following validations are automatically applied to the slide specification JSON (generated by LLM):

- Slide count (1–20 slides)
- Layout-field consistency (e.g., `two_content` requires `left`/`right`)
- Text length limits (title: 100 chars, body item: 200 chars, etc.)
- Audio file format (MP3/WAV) and size (max 50 MB)
- Estimated speaking duration check

## Notes

### Playback in LibreOffice Impress

Auto-advance (automatically moving to the next slide after audio finishes) **only works in PowerPoint (Windows / macOS)**.

**LibreOffice Impress does not support auto-advance**. This is a known limitation where LibreOffice does not correctly process PPTX timing settings (`advTm`) — see [Bug 101527](https://bugs.documentfoundation.org/show_bug.cgi?id=101527).

When using LibreOffice Impress:
- Advance slides **manually** (click or arrow keys)
- Or set auto-advance times manually via the "Slide Transition" panel in LibreOffice

### About Fonts

Templates use [Noto CJK](https://github.com/googlefonts/noto-cjk) fonts for Japanese text.
Available on Windows, macOS, and Linux. If not installed, OS default fonts will be used as fallback.
For optimal display, we recommend installing Noto Sans CJK JP in advance.

## License

MIT
