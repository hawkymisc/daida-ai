"""TDD: synthesize.py — 音声合成パイプラインテスト

TTSエンジンをモックし、ノート→音声ファイル生成のロジックを検証する。
ネットワーク通信は一切行わない。
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from daida_ai.lib.synthesize import synthesize_notes


@pytest.fixture
def mock_engine():
    """モックTTSエンジン"""
    engine = AsyncMock()

    async def fake_synthesize(text, output_path, voice=None):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 50)
        return output_path

    engine.synthesize.side_effect = fake_synthesize
    return engine


class Test正常系:
    """ノートから音声ファイルを生成する基本動作"""

    @pytest.mark.asyncio
    async def test_ノートありスライドの音声が生成される(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["こんにちは", "", "ありがとう"]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        assert len(results) == 3
        assert results[0] == audio_dir / "slide_000.mp3"
        assert results[1] is None  # 空ノートはスキップ
        assert results[2] == audio_dir / "slide_002.mp3"

    @pytest.mark.asyncio
    async def test_生成されたファイルが存在する(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["テスト"]
        audio_dir = tmp_output_dir / "audio"

        await synthesize_notes(notes, audio_dir, engine=mock_engine)

        assert (audio_dir / "slide_000.mp3").exists()

    @pytest.mark.asyncio
    async def test_出力ディレクトリが自動作成される(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["テスト"]
        audio_dir = tmp_output_dir / "nested" / "audio"

        await synthesize_notes(notes, audio_dir, engine=mock_engine)

        assert audio_dir.exists()

    @pytest.mark.asyncio
    async def test_voice引数がエンジンに渡される(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["テスト"]
        audio_dir = tmp_output_dir / "audio"

        await synthesize_notes(
            notes, audio_dir, engine=mock_engine, voice="ja-JP-KeitaNeural"
        )

        _, kwargs = mock_engine.synthesize.call_args
        assert kwargs.get("voice") == "ja-JP-KeitaNeural"

    @pytest.mark.asyncio
    async def test_エンジン名からエンジンを解決できる(
        self, tmp_output_dir: Path
    ):
        """engine引数の代わりにengine_name文字列を渡せる"""
        notes = ["テスト"]
        audio_dir = tmp_output_dir / "audio"

        with patch("daida_ai.lib.synthesize.get_engine") as mock_get:
            mock_eng = AsyncMock()

            async def fake_synth(text, output_path, voice=None):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"\x00" * 10)
                return output_path

            mock_eng.synthesize.side_effect = fake_synth
            mock_get.return_value = mock_eng

            await synthesize_notes(
                notes, audio_dir, engine_name="edge"
            )

            mock_get.assert_called_once_with("edge")


class Test空ノート処理:
    """空ノートやスペースのみのノートの処理"""

    @pytest.mark.asyncio
    async def test_空文字列はスキップされる(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["", "", ""]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        assert all(r is None for r in results)
        mock_engine.synthesize.assert_not_called()

    @pytest.mark.asyncio
    async def test_スペースのみのノートはスキップされる(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["  \t\n  "]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        assert results == [None]
        mock_engine.synthesize.assert_not_called()

    @pytest.mark.asyncio
    async def test_全スライド空でもエラーにならない(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = []
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        assert results == []


class Testファイル命名:
    """出力ファイルの命名規則"""

    @pytest.mark.asyncio
    async def test_slide_NNN_mp3形式で命名される(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = ["a"] * 5
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        expected_names = [f"slide_{i:03d}.mp3" for i in range(5)]
        actual_names = [r.name for r in results]
        assert actual_names == expected_names

    @pytest.mark.asyncio
    async def test_100スライド以上でも3桁ゼロ埋め(
        self, tmp_output_dir: Path, mock_engine
    ):
        notes = [""] * 99 + ["テスト"]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=mock_engine
        )

        assert results[99] == audio_dir / "slide_099.mp3"


class Testエラーハンドリング:
    """engine/engine_nameどちらも指定されない場合"""

    @pytest.mark.asyncio
    async def test_engine未指定でValueError(
        self, tmp_output_dir: Path
    ):
        with pytest.raises(ValueError, match="engine"):
            await synthesize_notes(
                ["テスト"], tmp_output_dir / "audio"
            )


class TestA4_TTS障害時フォールバック:
    """A4: TTS APIが一部スライドで失敗しても、成功分は保持される"""

    @pytest.fixture
    def failing_engine(self):
        """2番目のスライドで例外を投げるモックエンジン"""
        engine = AsyncMock()
        call_count = 0

        async def partial_fail(text, output_path, voice=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConnectionError("VOICEVOX connection refused")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 50)
            return output_path

        engine.synthesize.side_effect = partial_fail
        return engine

    @pytest.mark.asyncio
    async def test_一部スライドが失敗しても残りは生成される(
        self, tmp_output_dir: Path, failing_engine
    ):
        notes = ["スライド1", "スライド2", "スライド3"]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=failing_engine
        )

        assert results[0] is not None  # 成功
        assert results[1] is None      # 失敗→スキップ
        assert results[2] is not None  # 成功

    @pytest.mark.asyncio
    async def test_全スライド失敗でもクラッシュしない(
        self, tmp_output_dir: Path
    ):
        engine = AsyncMock()
        engine.synthesize.side_effect = ConnectionError("VOICEVOX down")

        notes = ["スライド1", "スライド2"]
        audio_dir = tmp_output_dir / "audio"

        results = await synthesize_notes(
            notes, audio_dir, engine=engine
        )

        assert all(r is None for r in results)

    @pytest.mark.asyncio
    async def test_失敗したスライドの情報がwarningsに含まれる(
        self, tmp_output_dir: Path, failing_engine
    ):
        import warnings

        notes = ["スライド1", "スライド2", "スライド3"]
        audio_dir = tmp_output_dir / "audio"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await synthesize_notes(
                notes, audio_dir, engine=failing_engine
            )

            tts_warnings = [x for x in w if "TTS" in str(x.message) or "slide" in str(x.message).lower()]
            assert len(tts_warnings) >= 1
