"""TDD: video_builder.py — 動画ビルダーテスト

MP4動画の生成・バリデーションを検証する。
外部ツール(ffmpeg/LibreOffice)を使うテストは integration マーカーで分離。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from pydub.generators import Sine

from daida_ai.lib.video_builder import (
    SlideClip,
    _DEFAULT_AUDIO_PADDING,
    _DEFAULT_SILENT_DURATION,
    build_clips,
    concat_clips,
    get_audio_duration,
    probe_video,
    render_slides,
    validate_video,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_png(tmp_dir: Path) -> Path:
    """偶数解像度のテスト画像 (640x480)"""
    path = tmp_dir / "slide.png"
    img = Image.new("RGB", (640, 480), color=(30, 30, 30))
    img.save(str(path))
    return path


@pytest.fixture
def odd_png(tmp_dir: Path) -> Path:
    """奇数解像度のテスト画像 (641x481)"""
    path = tmp_dir / "slide_odd.png"
    img = Image.new("RGB", (641, 481), color=(30, 30, 30))
    img.save(str(path))
    return path


@pytest.fixture
def sample_mp3(tmp_dir: Path) -> Path:
    """2秒のテスト用MP3ファイル"""
    path = tmp_dir / "audio.mp3"
    tone = Sine(440).to_audio_segment(duration=2000)
    tone.export(str(path), format="mp3")
    return path


@pytest.fixture
def short_mp3(tmp_dir: Path) -> Path:
    """0.5秒のテスト用MP3ファイル"""
    path = tmp_dir / "short.mp3"
    tone = Sine(440).to_audio_segment(duration=500)
    tone.export(str(path), format="mp3")
    return path


@pytest.fixture
def long_mp3(tmp_dir: Path) -> Path:
    """10秒のテスト用MP3ファイル"""
    path = tmp_dir / "long.mp3"
    tone = Sine(440).to_audio_segment(duration=10000)
    tone.export(str(path), format="mp3")
    return path


# ---------------------------------------------------------------------------
# get_audio_duration
# ---------------------------------------------------------------------------


class Test音声デュレーション取得:
    def test_MP3の実尺を取得できる(self, sample_mp3: Path):
        duration = get_audio_duration(sample_mp3)
        assert abs(duration - 2.0) < 0.1

    def test_短い音声の実尺を取得できる(self, short_mp3: Path):
        duration = get_audio_duration(short_mp3)
        assert abs(duration - 0.5) < 0.1

    def test_長い音声の実尺を取得できる(self, long_mp3: Path):
        duration = get_audio_duration(long_mp3)
        assert abs(duration - 10.0) < 0.1

    def test_存在しないファイルでFileNotFoundError(self, tmp_dir: Path):
        with pytest.raises(Exception):
            get_audio_duration(tmp_dir / "nonexistent.mp3")


# ---------------------------------------------------------------------------
# SlideClip
# ---------------------------------------------------------------------------


class TestSlideClipデータ:
    def test_音声ありクリップの属性(self, sample_png: Path, sample_mp3: Path):
        clip = SlideClip(0, sample_png, sample_mp3, 2.0)
        assert clip.slide_index == 0
        assert clip.image_path == sample_png
        assert clip.audio_path == sample_mp3
        assert clip.duration == 2.0

    def test_音声なしクリップの属性(self, sample_png: Path):
        clip = SlideClip(1, sample_png, None, 3.0)
        assert clip.audio_path is None
        assert clip.duration == 3.0

    def test_frozenでイミュータブル(self, sample_png: Path):
        clip = SlideClip(0, sample_png, None, 3.0)
        with pytest.raises(AttributeError):
            clip.duration = 5.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# render_slides (mocked)
# ---------------------------------------------------------------------------


class Testスライドレンダリング:
    def test_LibreOffice未インストールでFileNotFoundError(self, tmp_dir: Path):
        with patch("daida_ai.lib.video_builder.shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="LibreOffice not found"):
                render_slides(tmp_dir / "dummy.pptx", tmp_dir / "out")

    def test_PDF変換失敗でRuntimeError(self, tmp_dir: Path):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "conversion error"

        with (
            patch("daida_ai.lib.video_builder.shutil.which", return_value="/usr/bin/libreoffice"),
            patch("daida_ai.lib.video_builder.subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(RuntimeError, match="PPTX→PDF conversion failed"):
                render_slides(tmp_dir / "dummy.pptx", tmp_dir / "out")

    def test_PDF生成なしでRuntimeError(self, tmp_dir: Path):
        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("daida_ai.lib.video_builder.shutil.which", return_value="/usr/bin/libreoffice"),
            patch("daida_ai.lib.video_builder.subprocess.run", return_value=mock_result),
        ):
            with pytest.raises(RuntimeError, match="No PDF file generated"):
                render_slides(tmp_dir / "dummy.pptx", tmp_dir / "out")


# ---------------------------------------------------------------------------
# build_clips (integration: ffmpeg required)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testクリップ生成:
    def test_音声ありクリップを生成できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        out_dir = tmp_dir / "clips"

        result = build_clips(clips, out_dir, audio_padding=0)

        assert len(result) == 1
        assert result[0].exists()
        assert result[0].stat().st_size > 0

    def test_音声なしクリップを生成できる(self, tmp_dir: Path, sample_png: Path):
        clips = [SlideClip(0, sample_png, None, 3.0)]
        out_dir = tmp_dir / "clips"

        result = build_clips(clips, out_dir, audio_padding=0)

        assert len(result) == 1
        assert result[0].exists()

    def test_奇数解像度でも偶数化されて生成できる(
        self, tmp_dir: Path, odd_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, odd_png, sample_mp3, 2.0)]
        out_dir = tmp_dir / "clips"

        result = build_clips(clips, out_dir, audio_padding=0)

        assert len(result) == 1
        info = probe_video(result[0])
        assert info.width % 2 == 0
        assert info.height % 2 == 0

    def test_複数クリップを順番に生成できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [
            SlideClip(0, sample_png, sample_mp3, 2.0),
            SlideClip(1, sample_png, None, 3.0),
            SlideClip(2, sample_png, sample_mp3, 2.0),
        ]
        out_dir = tmp_dir / "clips"

        result = build_clips(clips, out_dir, audio_padding=0)

        assert len(result) == 3
        for i, p in enumerate(result):
            assert p.name == f"clip_{i:03d}.mp4"

    def test_存在しない音声ファイルはサイレント音声になる(
        self, tmp_dir: Path, sample_png: Path
    ):
        clips = [
            SlideClip(0, sample_png, tmp_dir / "nonexistent.mp3", 3.0),
        ]
        out_dir = tmp_dir / "clips"

        result = build_clips(clips, out_dir, audio_padding=0)

        assert len(result) == 1
        info = probe_video(result[0])
        # サイレント音声トラックが付く（concat時のストリーム不一致防止）
        assert info.audio_codec == "aac"
        assert info.nb_streams == 2


# ---------------------------------------------------------------------------
# concat_clips (integration: ffmpeg required)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testクリップ結合:
    def test_単一クリップでも結合できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clips_dir = tmp_dir / "clips"
        clip_paths = build_clips(clips, clips_dir, audio_padding=0)

        out_path = tmp_dir / "output.mp4"
        result = concat_clips(clip_paths, out_path)

        assert result == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_複数クリップを1本に結合できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [
            SlideClip(0, sample_png, sample_mp3, 2.0),
            SlideClip(1, sample_png, None, 1.0),
            SlideClip(2, sample_png, sample_mp3, 2.0),
        ]
        clips_dir = tmp_dir / "clips"
        clip_paths = build_clips(clips, clips_dir, audio_padding=0)

        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        # 2 + 1 + 2 = 5秒（±許容誤差）
        assert abs(info.duration - 5.0) < 1.5

    def test_空リストでValueError(self, tmp_dir: Path):
        with pytest.raises(ValueError, match="No clips to concatenate"):
            concat_clips([], tmp_dir / "output.mp4")

    def test_filelistは結合後に削除される(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clips_dir = tmp_dir / "clips"
        clip_paths = build_clips(clips, clips_dir, audio_padding=0)

        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        filelist = tmp_dir / "_filelist.txt"
        assert not filelist.exists()


# ---------------------------------------------------------------------------
# probe_video
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testプローブ:
    def test_音声ありクリップの情報を取得できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")

        info = probe_video(clip_paths[0])

        assert info.video_codec == "h264"
        assert info.audio_codec == "aac"
        assert info.width == 640
        assert info.height == 480
        assert info.file_size > 0
        assert info.nb_streams == 2

    def test_音声なしクリップもサイレント音声トラック付き(
        self, tmp_dir: Path, sample_png: Path
    ):
        clips = [SlideClip(0, sample_png, None, 1.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")

        info = probe_video(clip_paths[0])

        assert info.video_codec == "h264"
        assert info.audio_codec == "aac"
        assert info.nb_streams == 2

    def test_存在しないファイルでFileNotFoundError(self, tmp_dir: Path):
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            probe_video(tmp_dir / "nonexistent.mp4")


# ---------------------------------------------------------------------------
# validate_video
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testバリデーション:
    def test_正常なMP4はエラーなし(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        errors = validate_video(out_path)

        assert errors == []

    def test_存在しないファイルはエラー(self, tmp_dir: Path):
        errors = validate_video(tmp_dir / "nonexistent.mp4")
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_空ファイルはエラー(self, tmp_dir: Path):
        empty = tmp_dir / "empty.mp4"
        empty.write_bytes(b"")

        errors = validate_video(empty)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()

    def test_偶数解像度チェックを通過する(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert info.width % 2 == 0
        assert info.height % 2 == 0

        errors = validate_video(out_path)
        assert not any("Odd" in e for e in errors)

    def test_期待デュレーションが一致するとエラーなし(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        errors = validate_video(out_path, expected_duration=info.duration)
        assert errors == []

    def test_期待デュレーションが大きく乖離するとエラー(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        errors = validate_video(out_path, expected_duration=100.0)
        assert len(errors) == 1
        assert "Duration mismatch" in errors[0]

    def test_奇数解像度もpadフィルターで偶数化される(
        self, tmp_dir: Path, odd_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, odd_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        errors = validate_video(out_path)
        assert not any("Odd" in e for e in errors)

    def test_ffprobe未検出でもvalidateがクラッシュしない(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        with patch("daida_ai.lib.video_builder.shutil.which", return_value=None):
            errors = validate_video(out_path)

        assert len(errors) == 1
        assert "ffprobe" in errors[0].lower() or "cannot read" in errors[0].lower()

    def test_H264コーデックであること(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert info.video_codec == "h264"

        errors = validate_video(out_path)
        assert not any("codec" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# build_video (mocked render_slides, integration for ffmpeg)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testビルドパイプライン:
    def test_音声と画像から動画を生成できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        """render_slidesをモックし、ffmpegのクリップ生成〜結合をテスト。"""
        # 疑似スライド画像を準備
        slides_dir = tmp_dir / "slides"
        slides_dir.mkdir()
        for i in range(3):
            img = Image.new("RGB", (640, 480), color=(30 + i * 20, 30, 30))
            img.save(str(slides_dir / f"slide-{i + 1:02d}.png"))

        # 疑似音声を準備
        audio_dir = tmp_dir / "audio"
        audio_dir.mkdir()
        for i in range(3):
            tone = Sine(440).to_audio_segment(duration=1000)
            tone.export(str(audio_dir / f"slide_{i:03d}.mp3"), format="mp3")

        out_path = tmp_dir / "output.mp4"

        with patch(
            "daida_ai.lib.video_builder.render_slides",
            return_value=sorted(slides_dir.glob("*.png")),
        ):
            from daida_ai.lib.video_builder import build_video

            result = build_video(
                tmp_dir / "dummy.pptx",
                audio_dir,
                out_path,
                audio_padding=0,
            )

        assert result.video_path == out_path
        assert result.slide_count == 3
        assert result.audio_count == 3
        assert out_path.exists()

        errors = validate_video(out_path, expected_duration=result.expected_duration)
        assert errors == []

    def test_音声なしスライドはデフォルト秒数になる(
        self, tmp_dir: Path, sample_png: Path
    ):
        slides_dir = tmp_dir / "slides"
        slides_dir.mkdir()
        for i in range(2):
            img = Image.new("RGB", (640, 480), color=(50, 50, 50))
            img.save(str(slides_dir / f"slide-{i + 1:02d}.png"))

        audio_dir = tmp_dir / "audio"
        audio_dir.mkdir()
        # 音声なし

        out_path = tmp_dir / "output.mp4"

        with patch(
            "daida_ai.lib.video_builder.render_slides",
            return_value=sorted(slides_dir.glob("*.png")),
        ):
            from daida_ai.lib.video_builder import build_video

            result = build_video(tmp_dir / "dummy.pptx", audio_dir, out_path, audio_padding=0)

        assert result.slide_count == 2
        assert result.audio_count == 0

        info = probe_video(out_path)
        assert abs(info.duration - result.expected_duration) < 1.5
        # サイレント音声トラックが付く
        assert info.audio_codec == "aac"

    def test_混合スライドの合計デュレーション(
        self, tmp_dir: Path
    ):
        """音声あり(2s) + 音声なし(3s) + 音声あり(2s) = 約7秒"""
        slides_dir = tmp_dir / "slides"
        slides_dir.mkdir()
        for i in range(3):
            img = Image.new("RGB", (640, 480), color=(40, 40, 40))
            img.save(str(slides_dir / f"slide-{i + 1:02d}.png"))

        audio_dir = tmp_dir / "audio"
        audio_dir.mkdir()
        tone = Sine(440).to_audio_segment(duration=2000)
        tone.export(str(audio_dir / "slide_000.mp3"), format="mp3")
        # slide_001 は音声なし
        tone.export(str(audio_dir / "slide_002.mp3"), format="mp3")

        out_path = tmp_dir / "output.mp4"

        with patch(
            "daida_ai.lib.video_builder.render_slides",
            return_value=sorted(slides_dir.glob("*.png")),
        ):
            from daida_ai.lib.video_builder import build_video

            result = build_video(tmp_dir / "dummy.pptx", audio_dir, out_path, audio_padding=0)

        assert result.slide_count == 3
        assert result.audio_count == 2

        info = probe_video(out_path)
        # 2 + 3 + 2 = 7秒
        assert abs(info.duration - result.expected_duration) < 1.5

    def test_ワークディレクトリがクリーンアップされる(
        self, tmp_dir: Path, sample_png: Path
    ):
        slides_dir = tmp_dir / "slides"
        slides_dir.mkdir()
        img = Image.new("RGB", (640, 480), color=(50, 50, 50))
        img.save(str(slides_dir / "slide-01.png"))

        audio_dir = tmp_dir / "audio"
        audio_dir.mkdir()

        out_path = tmp_dir / "output.mp4"
        work_dir = out_path.parent / "_video_work"

        with patch(
            "daida_ai.lib.video_builder.render_slides",
            return_value=sorted(slides_dir.glob("*.png")),
        ):
            from daida_ai.lib.video_builder import build_video

            result = build_video(tmp_dir / "dummy.pptx", audio_dir, out_path, audio_padding=0)

        assert not work_dir.exists()
        assert result.video_path == out_path


# ---------------------------------------------------------------------------
# エッジケース
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Testエッジケース:
    def test_1枚のスライドで動画を生成できる(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        errors = validate_video(out_path)
        assert errors == []

    def test_全スライド無音で動画を生成できる(
        self, tmp_dir: Path, sample_png: Path
    ):
        clips = [
            SlideClip(0, sample_png, None, 2.0),
            SlideClip(1, sample_png, None, 2.0),
        ]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        # サイレント音声トラックが付く
        assert info.audio_codec == "aac"
        errors = validate_video(out_path)
        assert errors == []

    def test_短い音声でも動画を生成できる(
        self, tmp_dir: Path, sample_png: Path, short_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, short_mp3, 0.5)]
        clip_paths = build_clips(clips, tmp_dir / "clips")
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert info.duration > 0
        errors = validate_video(out_path)
        assert errors == []

    def test_長い音声でも動画を生成できる(
        self, tmp_dir: Path, sample_png: Path, long_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, long_mp3, 10.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=0)
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert abs(info.duration - 10.0) < 1.0
        errors = validate_video(out_path)
        assert errors == []

    def test_音声あり無し混合concatでストリーム一貫性(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        """音声あり→無音→音声ありでconcatしてもストリーム数が一貫する。"""
        clips = [
            SlideClip(0, sample_png, sample_mp3, 2.0),
            SlideClip(1, sample_png, None, 1.0),  # サイレント
            SlideClip(2, sample_png, sample_mp3, 2.0),
        ]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=0)

        # 全クリップが2ストリーム（video + audio）を持つ
        for p in clip_paths:
            info = probe_video(p)
            assert info.nb_streams == 2, f"{p.name} has {info.nb_streams} streams"

        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert info.nb_streams == 2
        assert info.audio_codec == "aac"
        errors = validate_video(out_path)
        assert errors == []


# ---------------------------------------------------------------------------
# 音声パディング
# ---------------------------------------------------------------------------


@pytest.mark.integration
class Test音声パディング:
    def test_パディング付きクリップは音声尺より長い(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        """2秒音声 + 1.5秒パディング = 3.5秒のクリップ。"""
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=1.5)

        info = probe_video(clip_paths[0])
        assert abs(info.duration - 3.5) < 0.5

    def test_パディング0で音声尺そのまま(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        clips = [SlideClip(0, sample_png, sample_mp3, 2.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=0)

        info = probe_video(clip_paths[0])
        assert abs(info.duration - 2.0) < 0.5

    def test_音声なしクリップにはパディングが付かない(
        self, tmp_dir: Path, sample_png: Path
    ):
        clips = [SlideClip(0, sample_png, None, 3.0)]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=1.5)

        info = probe_video(clip_paths[0])
        assert abs(info.duration - 3.0) < 0.5

    def test_混合スライドのパディング合計(
        self, tmp_dir: Path, sample_png: Path, sample_mp3: Path
    ):
        """音声あり(2+1.5) + 音声なし(3) + 音声あり(2+1.5) = 10秒"""
        clips = [
            SlideClip(0, sample_png, sample_mp3, 2.0),
            SlideClip(1, sample_png, None, 3.0),
            SlideClip(2, sample_png, sample_mp3, 2.0),
        ]
        clip_paths = build_clips(clips, tmp_dir / "clips", audio_padding=1.5)
        out_path = tmp_dir / "output.mp4"
        concat_clips(clip_paths, out_path)

        info = probe_video(out_path)
        assert abs(info.duration - 10.0) < 1.5

    def test_デフォルトパディングは1_5秒(self):
        assert _DEFAULT_AUDIO_PADDING == 1.5
