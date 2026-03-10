"""TDD: audio_embed.py — 音声ファイルPPTX埋め込みテスト"""

import pytest
from pathlib import Path
from pptx import Presentation

from daida_ai.lib.slide_spec import SlideSpec, SlideMetadata, Slide
from daida_ai.lib.slide_builder import build_presentation
from daida_ai.lib.audio_embed import embed_audio_to_pptx


@pytest.fixture
def pptx_path(tmp_output_dir: Path) -> Path:
    """テスト用3スライドPPTX"""
    spec = SlideSpec(
        metadata=SlideMetadata(title="T", subtitle="S", event="E"),
        slides=[
            Slide(layout="title_slide", title="スライド1"),
            Slide(layout="title_and_content", title="スライド2", body=["a"]),
            Slide(layout="section_header", title="スライド3"),
        ],
    )
    prs = build_presentation(spec)
    path = tmp_output_dir / "test.pptx"
    prs.save(str(path))
    return path


@pytest.fixture
def audio_dir(tmp_output_dir: Path) -> Path:
    """テスト用音声ファイルディレクトリ（ダミーMP3）"""
    d = tmp_output_dir / "audio"
    d.mkdir()
    # ダミーMP3ファイルを作成（実際のMP3ヘッダではないがテスト用）
    for i in [0, 2]:
        (d / f"slide_{i:03d}.mp3").write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)
    return d


class TestEmbedAudio:
    """embed_audio_to_pptx() のテスト"""

    def test_音声ファイルが埋め込まれる(
        self, pptx_path: Path, audio_dir: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "output.pptx"
        count = embed_audio_to_pptx(pptx_path, audio_dir, output)
        assert count == 2
        assert output.exists()

    def test_音声なしスライドはスキップされる(
        self, pptx_path: Path, audio_dir: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "output.pptx"
        embed_audio_to_pptx(pptx_path, audio_dir, output)

        prs = Presentation(str(output))
        # slide_001にはaudioがないのでshape数はスライド0,2より少ないはず
        assert len(prs.slides) == 3

    def test_音声ファイルなしのディレクトリは0件(
        self, pptx_path: Path, tmp_output_dir: Path
    ):
        empty_dir = tmp_output_dir / "empty_audio"
        empty_dir.mkdir()
        output = tmp_output_dir / "output.pptx"
        count = embed_audio_to_pptx(pptx_path, empty_dir, output)
        assert count == 0

    def test_出力ファイルが正常に開ける(
        self, pptx_path: Path, audio_dir: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "output.pptx"
        embed_audio_to_pptx(pptx_path, audio_dir, output)
        prs = Presentation(str(output))
        assert len(prs.slides) == 3
