"""TTSプラグインインターフェース"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    """音声合成エンジンの抽象基底クラス"""

    @abstractmethod
    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        """テキストを音声ファイルに変換する。

        Args:
            text: 音声合成するテキスト
            output_path: 出力ファイルパス
            voice: 音声名（Noneでデフォルト）

        Returns:
            生成された音声ファイルのパス
        """
        ...

    @abstractmethod
    def available_voices(self) -> list[str]:
        """利用可能な音声名の一覧を返す。"""
        ...


def get_engine(name: str) -> TTSEngine:
    """エンジン名からTTSEngineインスタンスを取得する。

    Args:
        name: "edge" or "voicevox"

    Raises:
        ValueError: 不正なエンジン名
    """
    if name == "edge":
        from daida_ai.lib.tts_edge import EdgeTTSEngine

        return EdgeTTSEngine()
    elif name == "voicevox":
        from daida_ai.lib.tts_voicevox import VoicevoxTTSEngine

        return VoicevoxTTSEngine()
    else:
        raise ValueError(f"Unknown engine: {name}")
