"""TDD: tts_engine.py — TTSプラグインインターフェーステスト"""

import pytest
from daida_ai.lib.tts_engine import TTSEngine, get_engine


class TestTTSEngineInterface:
    """TTSEngine抽象クラスのインターフェーステスト"""

    def test_TTSEngineは直接インスタンス化できない(self):
        with pytest.raises(TypeError):
            TTSEngine()

    def test_synthesizeメソッドが定義されている(self):
        assert hasattr(TTSEngine, "synthesize")

    def test_available_voicesメソッドが定義されている(self):
        assert hasattr(TTSEngine, "available_voices")


class TestGetEngine:
    """get_engine() ファクトリ関数テスト"""

    def test_edgeエンジンを取得できる(self):
        engine = get_engine("edge")
        assert isinstance(engine, TTSEngine)

    def test_voicevoxエンジンを取得できる(self):
        engine = get_engine("voicevox")
        assert isinstance(engine, TTSEngine)

    def test_elevenlabsエンジンを取得できる(self):
        engine = get_engine("elevenlabs")
        assert isinstance(engine, TTSEngine)

    def test_openaiエンジンを取得できる(self):
        engine = get_engine("openai")
        assert isinstance(engine, TTSEngine)

    def test_不正なエンジン名はValueError(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("invalid_engine")
