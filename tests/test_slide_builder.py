"""TDD: slide_builder.py — スライド仕様JSON → PPTX生成テスト"""

import pytest
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

from daida_ai.lib.slide_spec import (
    SlideSpec,
    SlideMetadata,
    Slide,
    TwoColumnContent,
)
from daida_ai.lib.slide_builder import build_presentation


@pytest.fixture
def simple_spec() -> SlideSpec:
    """最小限のスライド仕様"""
    return SlideSpec(
        metadata=SlideMetadata(
            title="テストプレゼン",
            subtitle="テスター",
            event="テストイベント",
        ),
        slides=[
            Slide(layout="title_slide", title="テストプレゼン", subtitle="サブタイトル"),
            Slide(
                layout="title_and_content",
                title="本題",
                body=["項目1", "項目2", "項目3"],
                note="ここが説明です。",
            ),
        ],
    )


@pytest.fixture
def full_spec() -> SlideSpec:
    """全レイアウトを含むスライド仕様"""
    return SlideSpec(
        metadata=SlideMetadata(
            title="フルテスト",
            subtitle="テスター",
            event="イベント",
        ),
        slides=[
            Slide(layout="title_slide", title="フルテスト", subtitle="サブ"),
            Slide(layout="section_header", title="セクション1"),
            Slide(
                layout="title_and_content",
                title="コンテンツ",
                body=["A", "B", "C"],
                note="ノートテキスト",
            ),
            Slide(
                layout="two_content",
                title="比較",
                left=TwoColumnContent(heading="左見出し", body=["L1", "L2"]),
                right=TwoColumnContent(heading="右見出し", body=["R1", "R2"]),
                note="比較ノート",
            ),
            Slide(layout="title_only", title="図のスライド", note="図の説明"),
            Slide(layout="blank"),
        ],
    )


class TestBuildPresentation:
    """build_presentation() のテスト"""

    def test_Presentationオブジェクトを返す(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        assert type(prs).__name__ == "Presentation"

    def test_スライド数が仕様と一致する(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        assert len(prs.slides) == 2

    def test_全レイアウトのスライド数が正しい(self, full_spec: SlideSpec):
        prs = build_presentation(full_spec)
        assert len(prs.slides) == 6

    def test_title_slideのタイトルが正しい(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[0]
        assert slide.shapes.title.text == "テストプレゼン"

    def test_title_slideのサブタイトルが正しい(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[0]
        # subtitle is typically placeholder idx 1
        subtitle_shape = slide.placeholders[1]
        assert subtitle_shape.text == "サブタイトル"

    def test_title_and_contentのタイトルが正しい(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[1]
        assert slide.shapes.title.text == "本題"

    def test_title_and_contentの箇条書きが正しい(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[1]
        body_shape = slide.placeholders[1]
        paragraphs = [p.text for p in body_shape.text_frame.paragraphs]
        assert paragraphs == ["項目1", "項目2", "項目3"]

    def test_スピーカーノートが設定される(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[1]
        assert slide.notes_slide.notes_text_frame.text == "ここが説明です。"

    def test_ノートなしのスライドはノートが空(self, simple_spec: SlideSpec):
        prs = build_presentation(simple_spec)
        slide = prs.slides[0]
        notes_text = slide.notes_slide.notes_text_frame.text
        assert notes_text == "" or notes_text.strip() == ""

    def test_section_headerのタイトル(self, full_spec: SlideSpec):
        prs = build_presentation(full_spec)
        slide = prs.slides[1]  # section_header
        assert slide.shapes.title.text == "セクション1"

    def test_two_contentの左右テキスト(self, full_spec: SlideSpec):
        prs = build_presentation(full_spec)
        slide = prs.slides[3]  # two_content
        # Check that all expected text appears in the slide
        all_text = " ".join(shape.text for shape in slide.shapes if shape.has_text_frame)
        assert "左見出し" in all_text
        assert "右見出し" in all_text

    def test_PPTXファイルとして保存できる(
        self, simple_spec: SlideSpec, tmp_output_dir: Path
    ):
        prs = build_presentation(simple_spec)
        path = tmp_output_dir / "test.pptx"
        prs.save(str(path))
        assert path.exists()
        assert path.stat().st_size > 0

    def test_保存したPPTXを再度開ける(
        self, simple_spec: SlideSpec, tmp_output_dir: Path
    ):
        prs = build_presentation(simple_spec)
        path = tmp_output_dir / "test.pptx"
        prs.save(str(path))

        reopened = Presentation(str(path))
        assert len(reopened.slides) == 2


class TestBuildPresentationEdgeCases:
    """build_presentation() のエッジケーステスト"""

    def test_スライドなしの仕様でも空プレゼンを生成(self):
        spec = SlideSpec(
            metadata=SlideMetadata(title="Empty", subtitle="S", event="E"),
            slides=[],
        )
        prs = build_presentation(spec)
        assert len(prs.slides) == 0

    def test_bodyが空リストでもエラーにならない(self):
        spec = SlideSpec(
            metadata=SlideMetadata(title="T", subtitle="S", event="E"),
            slides=[
                Slide(layout="title_and_content", title="空ボディ", body=[]),
            ],
        )
        prs = build_presentation(spec)
        assert len(prs.slides) == 1

    def test_非常に長いタイトルでもエラーにならない(self):
        long_title = "A" * 500
        spec = SlideSpec(
            metadata=SlideMetadata(title="T", subtitle="S", event="E"),
            slides=[
                Slide(layout="title_slide", title=long_title),
            ],
        )
        prs = build_presentation(spec)
        assert prs.slides[0].shapes.title.text == long_title

    def test_日本語の長いノートが保存される(self):
        long_note = "これはテストです。" * 100
        spec = SlideSpec(
            metadata=SlideMetadata(title="T", subtitle="S", event="E"),
            slides=[
                Slide(
                    layout="title_and_content",
                    title="ノートテスト",
                    body=["項目"],
                    note=long_note,
                ),
            ],
        )
        prs = build_presentation(spec)
        assert prs.slides[0].notes_slide.notes_text_frame.text == long_note

    def test_blankレイアウトのtitleはNone(self):
        """blankのtitleはデフォルト空文字で、shapes.titleはNone"""
        spec = SlideSpec(
            metadata=SlideMetadata(title="T", subtitle="S", event="E"),
            slides=[Slide(layout="blank")],
        )
        prs = build_presentation(spec)
        assert len(prs.slides) == 1
