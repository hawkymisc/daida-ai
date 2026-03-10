"""VOICEVOX API実装"""

from __future__ import annotations

from pathlib import Path

import httpx

from daida_ai.lib.tts_engine import TTSEngine
from daida_ai.lib.audio_utils import ensure_mp3

DEFAULT_HOST = "http://localhost:50021"
DEFAULT_SPEAKER_ID = 1  # ずんだもん（ノーマル）


class VoicevoxTTSEngine(TTSEngine):
    """VOICEVOX APIを使った音声合成エンジン"""

    def __init__(
        self, host: str = DEFAULT_HOST, speaker_id: int = DEFAULT_SPEAKER_ID
    ):
        self._host = host
        self._speaker_id = speaker_id

    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        speaker_id = int(voice) if voice else self._speaker_id

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 音声合成用クエリ作成
            query_resp = await client.post(
                f"{self._host}/audio_query",
                params={"text": text, "speaker": speaker_id},
            )
            query_resp.raise_for_status()
            query = query_resp.json()

            # 音声合成
            synth_resp = await client.post(
                f"{self._host}/synthesis",
                params={"speaker": speaker_id},
                json=query,
            )
            synth_resp.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # VOICEVOX APIはWAVを返すため、一旦WAVとして保存しMP3に変換
        wav_path = output_path.with_suffix(".wav")
        wav_path.write_bytes(synth_resp.content)
        mp3_path = ensure_mp3(wav_path)

        # 出力パスが.mp3と異なる場合にリネーム
        if mp3_path != output_path:
            mp3_path.rename(output_path)

        return output_path

    def available_voices(self) -> list[str]:
        return [
            "0",   # 四国めたん（ノーマル）
            "1",   # ずんだもん（ノーマル）
            "2",   # 四国めたん（あまあま）
            "3",   # ずんだもん（あまあま）
            "8",   # 春日部つむぎ
            "10",  # 雨晴はう
        ]
