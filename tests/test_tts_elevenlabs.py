"""ElevenLabs TTS実装のテスト

実ネットワーク通信は行わず、httpx.AsyncClientをモックして検証する。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from daida_ai.lib.tts_elevenlabs import (
    DEFAULT_API_BASE,
    DEFAULT_MODEL,
    DEFAULT_VOICE_ID,
    ElevenLabsTTSEngine,
)
from daida_ai.lib.tts_engine import TTSEngine


DUMMY_MP3_BYTES = b"\xff\xfb\x90\x00" + b"\x00" * 100


def _mock_httpx_client(response_bytes: bytes = DUMMY_MP3_BYTES):
    """httpx.AsyncClientのコンテキストマネージャをモックするパッチ。

    Returns: (patcher, post_mock)
    """
    response = MagicMock()
    response.content = response_bytes
    response.raise_for_status = MagicMock()

    post_mock = AsyncMock(return_value=response)
    client = MagicMock()
    client.post = post_mock
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    patcher = patch(
        "daida_ai.lib.tts_elevenlabs.httpx.AsyncClient", return_value=client
    )
    return patcher, post_mock


class TestElevenLabsInterface:
    def test_TTSEngineを継承している(self):
        engine = ElevenLabsTTSEngine(api_key="test")
        assert isinstance(engine, TTSEngine)

    def test_available_voicesがプリセット一覧を返す(self):
        engine = ElevenLabsTTSEngine(api_key="test")
        voices = engine.available_voices()
        assert isinstance(voices, list)
        assert DEFAULT_VOICE_ID in voices


class TestAPIKey:
    def test_APIキー未設定時はRuntimeError(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        engine = ElevenLabsTTSEngine(api_key=None)

        import asyncio

        with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
            asyncio.run(engine.synthesize("hi", tmp_path / "out.mp3"))

    def test_環境変数からAPIキーを読む(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "env-key")
        engine = ElevenLabsTTSEngine()
        assert engine._api_key == "env-key"

    def test_明示指定されたAPIキーが環境変数より優先される(self, monkeypatch):
        monkeypatch.setenv("ELEVENLABS_API_KEY", "env-key")
        engine = ElevenLabsTTSEngine(api_key="arg-key")
        assert engine._api_key == "arg-key"


class TestSynthesize:
    @pytest.mark.asyncio
    async def test_MP3ファイルが書き出される(self, tmp_path: Path):
        engine = ElevenLabsTTSEngine(api_key="test")
        output = tmp_path / "audio" / "out.mp3"

        patcher, _ = _mock_httpx_client()
        with patcher:
            result = await engine.synthesize("こんにちは", output)

        assert result == output
        assert output.exists()
        assert output.read_bytes() == DUMMY_MP3_BYTES

    @pytest.mark.asyncio
    async def test_親ディレクトリが自動作成される(self, tmp_path: Path):
        engine = ElevenLabsTTSEngine(api_key="test")
        output = tmp_path / "nested" / "dir" / "out.mp3"

        patcher, _ = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", output)

        assert output.parent.exists()

    @pytest.mark.asyncio
    async def test_voice引数がURLのvoice_idに反映される(self, tmp_path: Path):
        engine = ElevenLabsTTSEngine(api_key="test")
        custom_voice_id = "MY_CLONED_VOICE_123"

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize(
                "hi", tmp_path / "out.mp3", voice=custom_voice_id
            )

        # post(url, headers=..., params=..., json=...) の url を検証
        called_url = post_mock.call_args.args[0]
        assert custom_voice_id in called_url
        assert called_url.startswith(DEFAULT_API_BASE)

    @pytest.mark.asyncio
    async def test_voice未指定時はデフォルトvoice_idが使われる(
        self, tmp_path: Path
    ):
        engine = ElevenLabsTTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        called_url = post_mock.call_args.args[0]
        assert DEFAULT_VOICE_ID in called_url

    @pytest.mark.asyncio
    async def test_APIキーがxi_api_keyヘッダで送られる(self, tmp_path: Path):
        engine = ElevenLabsTTSEngine(api_key="my-secret-key")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        headers = post_mock.call_args.kwargs["headers"]
        assert headers["xi-api-key"] == "my-secret-key"

    @pytest.mark.asyncio
    async def test_リクエストボディにテキストとモデルが含まれる(
        self, tmp_path: Path
    ):
        engine = ElevenLabsTTSEngine(api_key="test")

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("読み上げる文", tmp_path / "out.mp3")

        body = post_mock.call_args.kwargs["json"]
        assert body["text"] == "読み上げる文"
        assert body["model_id"] == DEFAULT_MODEL
        assert "voice_settings" in body

    @pytest.mark.asyncio
    async def test_カスタムAPIベースURLが利用される(self, tmp_path: Path):
        engine = ElevenLabsTTSEngine(
            api_key="test", api_base="https://proxy.example.com/v1"
        )

        patcher, post_mock = _mock_httpx_client()
        with patcher:
            await engine.synthesize("hi", tmp_path / "out.mp3")

        called_url = post_mock.call_args.args[0]
        assert called_url.startswith("https://proxy.example.com/v1/")
