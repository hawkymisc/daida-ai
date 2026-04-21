"""ElevenLabs TTS実装

ElevenLabsのText-to-Speech APIを用いて音声を合成する。
ユーザーのVoice Clone資産（カスタムvoice_id）をそのまま利用できる。

環境変数:
    ELEVENLABS_API_KEY: APIキー（必須）
    ELEVENLABS_API_BASE: APIベースURL（省略時は公式エンドポイント）

voice引数:
    ElevenLabsのvoice_id（例: "21m00Tcm4TlvDq8ikWAM"）。
    ユーザーが作成したVoice Cloneのvoice_idもそのまま指定可能。
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from daida_ai.lib.tts_engine import TTSEngine

DEFAULT_API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"
# "Rachel" - ElevenLabsの標準プリセット音声
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsTTSEngine(TTSEngine):
    """ElevenLabs APIを使った音声合成エンジン"""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        default_voice: str = DEFAULT_VOICE_ID,
        api_base: str | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self._model = model
        self._default_voice = default_voice
        self._api_base = (
            api_base
            or os.environ.get("ELEVENLABS_API_BASE")
            or DEFAULT_API_BASE
        ).rstrip("/")
        self._output_format = output_format
        self._voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost,
        }

    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        if not self._api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY is not set. "
                "Set the environment variable or pass api_key explicitly."
            )

        voice_id = voice or self._default_voice
        url = f"{self._api_base}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self._api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self._model,
            "voice_settings": self._voice_settings,
        }
        params = {"output_format": self._output_format}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url, headers=headers, params=params, json=payload
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return output_path

    def available_voices(self) -> list[str]:
        """ElevenLabsのデフォルトプリセット音声のvoice_id一覧。

        Voice CloneやAPI経由で取得可能な全音声は含まない。
        ユーザー独自のVoice Cloneを使う場合はvoice_idを直接指定すること。
        """
        return [
            "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "AZnzlk1XvdvUeBnXmlld",  # Domi
            "EXAVITQu4vr4xnSDxMaL",  # Bella
            "ErXwobaYiN019PkySvjV",  # Antoni
            "MF3mGyEYCl7XYWbV9V6O",  # Elli
            "TxGEqnHWrfWFTfGW9XjX",  # Josh
            "VR6AewLTigWG4xSOukaG",  # Arnold
            "pNInz6obpgDQGcFmaJgB",  # Adam
            "yoZ06aMxZJJ28mfd3POQ",  # Sam
        ]
