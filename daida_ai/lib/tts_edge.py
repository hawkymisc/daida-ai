"""edge-tts実装"""

from __future__ import annotations

from pathlib import Path

import edge_tts

from daida_ai.lib.tts_engine import TTSEngine

DEFAULT_VOICE = "ja-JP-NanamiNeural"


class EdgeTTSEngine(TTSEngine):
    """Microsoft Edge TTSを使った音声合成エンジン"""

    def __init__(self, default_voice: str = DEFAULT_VOICE):
        self._default_voice = default_voice

    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        voice = voice or self._default_voice
        communicate = edge_tts.Communicate(text, voice)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))
        return output_path

    def available_voices(self) -> list[str]:
        return [
            "ja-JP-NanamiNeural",
            "ja-JP-KeitaNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
        ]
