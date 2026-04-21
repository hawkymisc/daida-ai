"""OpenAI TTS実装

OpenAIのText-to-Speech API (/v1/audio/speech) を用いて音声を合成する。
OpenAI互換APIエンドポイントを提供するサードパーティ（例: ローカルLLM向け
TTS互換サーバ）もAPIベースURLを差し替えることで利用可能。

環境変数:
    OPENAI_API_KEY: APIキー（必須）
    OPENAI_API_BASE: APIベースURL（省略時は公式エンドポイント）
    OPENAI_TTS_MODEL: モデル名（省略時はtts-1）

voice引数:
    OpenAI公式のプリセット音声名
    （alloy, echo, fable, onyx, nova, shimmer など）、
    または互換サーバ側でサポートされるカスタム音声名。
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from daida_ai.lib.tts_engine import TTSEngine

DEFAULT_API_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "tts-1"
DEFAULT_VOICE = "alloy"
DEFAULT_RESPONSE_FORMAT = "mp3"


class OpenAITTSEngine(TTSEngine):
    """OpenAI Text-to-Speech APIを使った音声合成エンジン"""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        default_voice: str = DEFAULT_VOICE,
        api_base: str | None = None,
        response_format: str = DEFAULT_RESPONSE_FORMAT,
        speed: float = 1.0,
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = (
            model or os.environ.get("OPENAI_TTS_MODEL") or DEFAULT_MODEL
        )
        self._default_voice = default_voice
        self._api_base = (
            api_base
            or os.environ.get("OPENAI_API_BASE")
            or DEFAULT_API_BASE
        ).rstrip("/")
        self._response_format = response_format
        self._speed = speed

    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Set the environment variable or pass api_key explicitly."
            )

        voice_name = voice or self._default_voice
        url = f"{self._api_base}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": text,
            "voice": voice_name,
            "response_format": self._response_format,
            "speed": self._speed,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            audio_bytes = resp.content

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        return output_path

    def available_voices(self) -> list[str]:
        """OpenAIのプリセット音声一覧。

        OpenAI公式TTSはVoice Cloneに非対応のため、プリセット音声のみ返す。
        OpenAI互換サーバ（独自Voice Cloneあり）を使う場合は、
        voice引数にカスタム音声名を直接指定すること。
        """
        return [
            "alloy",
            "ash",
            "ballad",
            "coral",
            "echo",
            "fable",
            "onyx",
            "nova",
            "sage",
            "shimmer",
            "verse",
        ]
