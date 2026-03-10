"""TDD: write_talk_script.py — スピーカーノート読み書きテスト"""

import pytest
from pathlib import Path
from pptx import Presentation

from daida_ai.lib.slide_spec import SlideSpec, SlideMetadata, Slide
from daida_ai.lib.slide_builder import build_presentation
from daida_ai.lib.talk_script import read_notes, write_notes


@pytest.fixture
def pptx_with_notes(tmp_output_dir: Path) -> Path:
    """ノート付きPPTXファイル"""
    spec = SlideSpec(
        metadata=SlideMetadata(title="T", subtitle="S", event="E"),
        slides=[
            Slide(layout="title_slide", title="タイトル", note="オープニングトーク"),
            Slide(
                layout="title_and_content",
                title="本題",
                body=["A", "B"],
                note="本題の説明です。",
            ),
            Slide(layout="section_header", title="まとめ"),
        ],
    )
    prs = build_presentation(spec)
    path = tmp_output_dir / "notes.pptx"
    prs.save(str(path))
    return path


class TestReadNotes:
    """read_notes(): PPTXからスピーカーノート一覧を取得"""

    def test_ノートのあるスライドのテキストを取得できる(
        self, pptx_with_notes: Path
    ):
        notes = read_notes(pptx_with_notes)
        assert notes[0] == "オープニングトーク"
        assert notes[1] == "本題の説明です。"

    def test_ノートのないスライドは空文字(self, pptx_with_notes: Path):
        notes = read_notes(pptx_with_notes)
        assert notes[2] == ""

    def test_スライド数と同じ長さのリストを返す(self, pptx_with_notes: Path):
        notes = read_notes(pptx_with_notes)
        assert len(notes) == 3

    def test_存在しないファイルはFileNotFoundError(self, tmp_output_dir: Path):
        with pytest.raises(FileNotFoundError):
            read_notes(tmp_output_dir / "nonexistent.pptx")


class TestWriteNotes:
    """write_notes(): PPTXのスピーカーノートを上書き"""

    def test_ノートを上書きできる(self, pptx_with_notes: Path):
        new_notes = ["新しいオープニング", "新しい本題", "新しいまとめ"]
        write_notes(pptx_with_notes, new_notes, pptx_with_notes)

        result = read_notes(pptx_with_notes)
        assert result == new_notes

    def test_別ファイルに保存できる(
        self, pptx_with_notes: Path, tmp_output_dir: Path
    ):
        output_path = tmp_output_dir / "updated.pptx"
        new_notes = ["A", "B", "C"]
        write_notes(pptx_with_notes, new_notes, output_path)

        assert output_path.exists()
        result = read_notes(output_path)
        assert result == new_notes

    def test_ノート数がスライド数と異なるとValueError(
        self, pptx_with_notes: Path
    ):
        with pytest.raises(ValueError, match="スライド数.*一致しません"):
            write_notes(pptx_with_notes, ["only one"], pptx_with_notes)

    def test_空文字ノートでスピーカーノートをクリアできる(
        self, pptx_with_notes: Path
    ):
        write_notes(pptx_with_notes, ["", "", ""], pptx_with_notes)
        result = read_notes(pptx_with_notes)
        assert all(n == "" for n in result)

    def test_日本語の長いノートを書き込める(
        self, pptx_with_notes: Path
    ):
        long_note = "これはテストです。" * 200
        write_notes(
            pptx_with_notes,
            [long_note, "", ""],
            pptx_with_notes,
        )
        result = read_notes(pptx_with_notes)
        assert result[0] == long_note
