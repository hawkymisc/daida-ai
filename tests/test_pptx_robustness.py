"""TDD: PPTX生成の堅牢性テスト

フォント・テキスト長・音声バリデーション・発話時間推定の
改善を検証するテスト群。
"""

import pytest
from pathlib import Path

from daida_ai.lib.template_builder import TEMPLATE_DESIGNS
from daida_ai.lib.slide_spec import (
    validate_slide_spec,
    MAX_TITLE_LENGTH,
    MAX_SUBTITLE_LENGTH,
    MAX_BODY_ITEM_LENGTH,
)
from daida_ai.lib.audio_embed import _validate_audio_file
from daida_ai.lib.slideshow import _estimate_reading_time_ms
from tests.conftest import DUMMY_MP3_BYTES_SHORT


def _make_valid_spec(*, title="テスト", body=None, subtitle=None):
    """テスト用の最小限のスライド仕様辞書を作成"""
    slide = {
        "layout": "title_and_content",
        "title": title,
        "note": "テスト用のノートです",
    }
    if body is not None:
        slide["body"] = body
    if subtitle is not None:
        slide["subtitle"] = subtitle
    return {
        "metadata": {"title": "テストプレゼン"},
        "slides": [slide],
    }


# ---------------------------------------------------------------------------
# 1. フォント
# ---------------------------------------------------------------------------
class Testフォント設定:
    """テンプレートの日本語フォントがクロスプラットフォーム対応であること"""

    @pytest.mark.parametrize("name", ["tech", "casual", "formal"])
    def test_日本語フォントにNoto系が設定されている(self, name: str):
        design = TEMPLATE_DESIGNS[name]

        major = design["major_font_jpan"]
        minor = design["minor_font_jpan"]

        assert "Noto" in major, f"{name} major_font_jpan should use Noto: {major}"
        assert "Noto" in minor, f"{name} minor_font_jpan should use Noto: {minor}"

    def test_formalのmajorフォントはSerifである(self):
        design = TEMPLATE_DESIGNS["formal"]
        assert "Serif" in design["major_font_jpan"]


# ---------------------------------------------------------------------------
# 2. テキストオーバーフロー
# ---------------------------------------------------------------------------
class Testテキスト長バリデーション:
    """タイトル・サブタイトル・本文項目の文字数上限"""

    def test_タイトルが上限以内なら通る(self):
        spec = _make_valid_spec(title="あ" * MAX_TITLE_LENGTH)
        result = validate_slide_spec(spec)
        assert result.slides[0].title == "あ" * MAX_TITLE_LENGTH

    def test_タイトルが上限超過でValueError(self):
        spec = _make_valid_spec(title="あ" * (MAX_TITLE_LENGTH + 1))
        with pytest.raises(ValueError, match="title exceeds"):
            validate_slide_spec(spec)

    def test_サブタイトルが上限超過でValueError(self):
        spec = _make_valid_spec(subtitle="あ" * (MAX_SUBTITLE_LENGTH + 1))
        with pytest.raises(ValueError, match="subtitle exceeds"):
            validate_slide_spec(spec)

    def test_body項目が上限超過でValueError(self):
        spec = _make_valid_spec(body=["あ" * (MAX_BODY_ITEM_LENGTH + 1)])
        with pytest.raises(ValueError, match="body.*exceeds"):
            validate_slide_spec(spec)

    def test_body項目が上限以内なら通る(self):
        spec = _make_valid_spec(body=["あ" * MAX_BODY_ITEM_LENGTH])
        result = validate_slide_spec(spec)
        assert len(result.slides[0].body[0]) == MAX_BODY_ITEM_LENGTH


# ---------------------------------------------------------------------------
# 3. 音声ファイルバリデーション
# ---------------------------------------------------------------------------
class Test音声バリデーション:
    """MP3/WAV形式チェックとサイズ上限"""

    def test_正常なMP3ファイルは通る(self, tmp_output_dir: Path):
        mp3 = tmp_output_dir / "test.mp3"
        mp3.write_bytes(DUMMY_MP3_BYTES_SHORT)

        _validate_audio_file(mp3)  # 例外なし

    def test_WAVヘッダのファイルは通る(self, tmp_output_dir: Path):
        wav = tmp_output_dir / "test.wav"
        wav.write_bytes(b"RIFF" + b"\x00" * 100)

        _validate_audio_file(wav)  # 例外なし

    def test_ID3タグ付きMP3は通る(self, tmp_output_dir: Path):
        mp3 = tmp_output_dir / "test.mp3"
        mp3.write_bytes(b"ID3" + b"\x00" * 100)

        _validate_audio_file(mp3)  # 例外なし

    def test_不正なヘッダでValueError(self, tmp_output_dir: Path):
        bad = tmp_output_dir / "test.mp3"
        bad.write_bytes(b"JUNK" + b"\x00" * 100)

        with pytest.raises(ValueError, match="Not a valid audio"):
            _validate_audio_file(bad)

    def test_小さすぎるファイルでValueError(self, tmp_output_dir: Path):
        tiny = tmp_output_dir / "test.mp3"
        tiny.write_bytes(b"\xff\xfb")

        with pytest.raises(ValueError, match="too small"):
            _validate_audio_file(tiny)


# ---------------------------------------------------------------------------
# 5. 発話時間推定
# ---------------------------------------------------------------------------
class Test発話時間推定:
    """日英混在テキストでの推定精度"""

    def test_日本語のみのテキスト(self):
        text = "あ" * 50  # 50 CJK chars / 5.0 = 10秒
        result = _estimate_reading_time_ms(text)
        assert result == 10000

    def test_英語のみのテキスト(self):
        text = "a" * 150  # 150 Latin / 15.0 = 10秒
        result = _estimate_reading_time_ms(text)
        assert result == 10000

    def test_日英混在テキストはCJKとLatinを別レートで計算(self):
        text = "あ" * 50 + "a" * 150
        result = _estimate_reading_time_ms(text)
        # CJK: 50/5=10秒, Latin: 150/15=10秒 → 合計20秒
        assert result == 20000

    def test_空文字列は元レートでフォールバック(self):
        # 記号のみ: CJK=0, Latin=0 → fallback = len/5
        text = "..." * 10  # 30文字 → 30/5 = 6秒
        result = _estimate_reading_time_ms(text)
        assert result == 6000

    def test_全角記号はCJKとしてカウントされる(self):
        text = "！＃＄"  # 全角記号 (0xFF00-0xFFEF)
        result = _estimate_reading_time_ms(text)
        assert result == pytest.approx(600, abs=100)
