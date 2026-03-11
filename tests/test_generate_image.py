"""TDD: generate_image.py — Gemini画像生成スクリプトのテスト"""

import base64
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "daida-ai" / "scripts"))

from generate_image import (
    generate_image,
    ImageGenerationError,
    MODELS,
    VALID_ASPECT_RATIOS,
    VALID_SIZES,
    DEFAULT_TIMEOUT,
)


def _make_api_response(*, image_data: bytes = b"\x89PNG\r\n", text: str | None = None):
    """Gemini API の成功レスポンスを模倣する辞書を返す。"""
    parts = []
    if image_data:
        parts.append({
            "inlineData": {
                "mimeType": "image/png",
                "data": base64.b64encode(image_data).decode(),
            }
        })
    if text:
        parts.append({"text": text})
    return {
        "candidates": [{"content": {"parts": parts}}],
    }


class TestPayloadStructure:
    """APIリクエストペイロードの構造を検証する"""

    def test_contentsにrole_userが含まれる(self, tmp_path, monkeypatch):
        """Gemini APIが要求する role フィールドが含まれる"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        captured_payload = {}

        def mock_urlopen(req, timeout=None):
            captured_payload.update(json.loads(req.data.decode("utf-8")))
            resp = MagicMock()
            resp.read.return_value = json.dumps(_make_api_response()).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            generate_image(
                prompt="test prompt",
                output_path=str(tmp_path / "out.png"),
            )

        contents = captured_payload["contents"]
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "test prompt"

    def test_generationConfigが正しく設定される(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        captured_payload = {}

        def mock_urlopen(req, timeout=None):
            captured_payload.update(json.loads(req.data.decode("utf-8")))
            resp = MagicMock()
            resp.read.return_value = json.dumps(_make_api_response()).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            generate_image(
                prompt="test",
                aspect_ratio="16:9",
                image_size="2K",
                output_path=str(tmp_path / "out.png"),
            )

        cfg = captured_payload["generationConfig"]
        assert cfg["imageConfig"]["aspectRatio"] == "16:9"
        assert cfg["imageConfig"]["imageSize"] == "2K"

    def test_タイムアウトが渡される(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        captured_timeout = {}

        def mock_urlopen(req, timeout=None):
            captured_timeout["value"] = timeout
            resp = MagicMock()
            resp.read.return_value = json.dumps(_make_api_response()).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            generate_image(
                prompt="test",
                output_path=str(tmp_path / "out.png"),
                timeout=30,
            )

        assert captured_timeout["value"] == 30

    def test_デフォルトタイムアウトは60秒(self):
        assert DEFAULT_TIMEOUT == 60


class TestImageSaving:
    """画像ファイルの保存を検証する"""

    def test_画像が正しく保存される(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        image_bytes = b"\x89PNG_TEST_DATA"

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps(
                _make_api_response(image_data=image_bytes)
            ).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            result = generate_image(
                prompt="test",
                output_path=str(tmp_path / "result.png"),
            )

        assert Path(result).exists()
        assert Path(result).read_bytes() == image_bytes

    def test_出力ディレクトリが自動作成される(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps(_make_api_response()).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        nested = tmp_path / "a" / "b" / "c" / "out.png"
        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            result = generate_image(prompt="test", output_path=str(nested))

        assert Path(result).exists()


class TestErrorHandling:
    """エラーハンドリングを検証する（例外ベース）"""

    def test_GEMINI_API_KEY未設定でImageGenerationError(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ImageGenerationError, match="GEMINI_API_KEY"):
            generate_image(prompt="test")

    def test_HTTPErrorでImageGenerationError(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        def mock_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                url="http://test", code=400, msg="Bad Request",
                hdrs=None, fp=MagicMock(read=lambda: b"error body"),
            )

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(ImageGenerationError, match="API error 400"):
                generate_image(prompt="test", output_path=str(tmp_path / "out.png"))

    def test_URLErrorでImageGenerationError(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        def mock_urlopen(req, timeout=None):
            raise urllib.error.URLError("DNS resolution failed")

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(ImageGenerationError, match="Network error"):
                generate_image(prompt="test", output_path=str(tmp_path / "out.png"))

    def test_TimeoutErrorでImageGenerationError(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        def mock_urlopen(req, timeout=None):
            raise TimeoutError("Connection timed out")

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(ImageGenerationError, match="Network error"):
                generate_image(prompt="test", output_path=str(tmp_path / "out.png"))

    def test_画像なしレスポンスでImageGenerationError(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        empty_response = {"candidates": [{"content": {"parts": [{"text": "no image"}]}}]}

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps(empty_response).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(ImageGenerationError, match="No image data"):
                generate_image(prompt="test", output_path=str(tmp_path / "out.png"))

    def test_candidatesが空でImageGenerationError(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        def mock_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json.dumps({"candidates": []}).encode()
            resp.__enter__ = lambda s: resp
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch("generate_image.urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(ImageGenerationError, match="No candidates"):
                generate_image(prompt="test", output_path=str(tmp_path / "out.png"))


class TestModelAliases:
    """モデルエイリアスの定数を検証する"""

    def test_全エイリアスが定義されている(self):
        assert "pro" in MODELS
        assert "flash" in MODELS
        assert "legacy" in MODELS

    def test_アスペクト比に16_9が含まれる(self):
        assert "16:9" in VALID_ASPECT_RATIOS

    def test_サイズに1Kが含まれる(self):
        assert "1K" in VALID_SIZES
