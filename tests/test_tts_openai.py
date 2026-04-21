"""OpenAI TTS実装のテスト

実ネットワーク通信は行わず、httpx.AsyncClientをモックして検証する。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from daida_ai.lib.tts_openai import (
    DEFAULT_API_BASE,
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    OpenAITTSEngine,
)
from daida_ai.lib.tts_engine import TTSEngine


DUMMY_MP3_BYTES = b"\xff\xfb\x90\x00" + b"\x00" * 100


def _mock_httpx_client(response_bytes: bytes = DUMMY_MP3_BYTES):
    response = MagicMock()
    response.content = response_bytes
    response.raise_for_status = MagicMock()

    post_mock = AsyncMock(return_value=response)
    client = MagicMock()
    client.post = post_mock
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    patcher = patch(
        "daida_ai.lib.tts_openai.httpx.AsyncClient", return_value=client
    )
    return patcher, post_mock


class TestOpenAIInterface:
    def test_TTSEngineを継承している(self):
        engine = OpenAITTSEngine(api_key="test")
        assert isinstance(engine, TTSEngine)

    def test_available_voicesがプリセット一覧を返す(self):
        engine = OpenAITTSEngine(api_key="test")
        voices = engine.available_voices()
        assert isinstance(voices, list)
        assert DEFAULT_VOICE in voices


class TestAPIKey:
    def test_APIキー未設定時はRuntimeError(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        engine = OpenAITTSEngine(api_key=None)

        import asyncio

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            asyncio.run(engine.synthesize("hi", tmp_path / "out.mp3"))

    def test_環境変数からAPIキーを読む(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        engine = OpenAITTSEngine()
        assert engine._api_key == "env-key"

    def test_明示指定されたAPIキーが環境変数より優先される(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        engine = OpenAITTSEngine(api_key="arg-key")
        assert engine._api_key == "arg-key"


class TestSynthesize:
    @pytest.mark.asyncio
    async def test_MP3ファイルが書き出される(self, tmp_path: Path):
        engine = OpenAITTSEngine(api_key="test")
        output = tmp_path / "audio" / "out.mp3"

        patcher, _ = _mock_httpx_client()
        with patcher:
            result = await engine.synthesize("こんにちは", output)

        assert result == output
        assert output.exists()
        assert output.read_bytes() == DUMMY_MP3_BYTES

    @pytest.mark.asyncio
    async def test_親ディレクトリが自動作成される(self, tmp_path: Path):
        engine = OpenAITTSEngine(api_key="test")
        output = tmp_path / "nested" / "dir" / "out.mp3"

        patcher, _ = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", output)

        assert output.parent.exists()

    @pytest.mark.asyncio
    async def test_voice引数がボディのvoiceに反映される(self, tmp_path: Path):
        engine = OpenAITTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize(
                "hi", tmp_path / "out.mp3", voice="nova"
            )

        body = post_mock.call_args.kwargs["json"]
        assert body["voice"] == "nova"

    @pytest.mark.asyncio
    async def test_voice未指定時はデフォルトvoiceが使われる(
        self, tmp_path: Path
    ):
        engine = OpenAITTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        body = post_mock.call_args.kwargs["json"]
        assert body["voice"] == DEFAULT_VOICE

    @pytest.mark.asyncio
    async def test_AuthorizationヘッダにBearerトークンが付く(
        self, tmp_path: Path
    ):
        engine = OpenAITTSEngine(api_key="my-secret-key")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        headers = post_mock.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-secret-key"

    @pytest.mark.asyncio
    async def test_リクエストボディにinputとmodelが含まれる(
        self, tmp_path: Path
    ):
        engine = OpenAITTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("読み上げる文", tmp_path / "out.mp3")

        body = post_mock.call_args.kwargs["json"]
        assert body["input"] == "読み上げる文"
        assert body["model"] == DEFAULT_MODEL
        assert body["response_format"] == "mp3"

    @pytest.mark.asyncio
    async def test_カスタムAPIベースURLが利用される(self, tmp_path: Path):
        engine = OpenAITTSEngine(
            api_key="test", api_base="https://proxy.example.com/v1"
        )

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        called_url = post_mock.call_args.args[0]
        assert called_url == "https://proxy.example.com/v1/audio/speech"

    @pytest.mark.asyncio
    async def test_エンドポイントがaudio_speech(self, tmp_path: Path):
        engine = OpenAITTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        called_url = post_mock.call_args.args[0]
        assert called_url == f"{DEFAULT_API_BASE}/audio/speech"

    @pytest.mark.asyncio
    async def test_環境変数OPENAI_TTS_MODELが使われる(
        self, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_TTS_MODEL", "tts-1-hd")
        engine = OpenAITTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        body = post_mock.call_args.kwargs["json"]
        assert body["model"] == "tts-1-hd"
