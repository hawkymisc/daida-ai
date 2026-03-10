"""TDD: enrich_outline.py — スライド仕様JSONのスキーマバリデーション"""

import json
import pytest
from pathlib import Path

from daida_ai.lib.slide_spec import (
    SlideSpec,
    SlideMetadata,
    Slide,
    TwoColumnContent,
    validate_slide_spec,
    load_slide_spec,
    save_slide_spec,
)


@pytest.fixture
def valid_spec_dict() -> dict:
    """有効なスライド仕様の辞書"""
    return {
        "metadata": {
            "title": "Claude Codeで変わる開発体験",
            "subtitle": "Hiroki Wakamatsu",
            "event": "Tech LT #42",
            "template": "tech",
        },
        "slides": [
            {
                "layout": "title_slide",
                "title": "Claude Codeで変わる開発体験",
                "subtitle": "2026/03/10 @ Tech LT #42",
            },
            {
                "layout": "section_header",
                "title": "なぜClaude Codeなのか",
            },
            {
                "layout": "title_and_content",
                "title": "背景: 従来の課題",
                "body": [
                    "処理速度が10倍遅い",
                    "メンテナンスコスト年間500万円",
                    "スケーラビリティの限界",
                ],
                "note": "まず従来の課題を3つ挙げます。",
            },
            {
                "layout": "two_content",
                "title": "Before / After",
                "left": {
                    "heading": "従来",
                    "body": ["手動デプロイ", "30分/回"],
                },
                "right": {
                    "heading": "新手法",
                    "body": ["自動CI/CD", "3分/回"],
                },
                "note": "比較してみましょう。",
            },
            {
                "layout": "title_only",
                "title": "アーキテクチャ図",
                "note": "ここに図を挿入。",
            },
        ],
    }


class TestSlideMetadata:
    """SlideMetadataのバリデーション"""

    def test_有効なメタデータを作成できる(self):
        meta = SlideMetadata(
            title="Test", subtitle="Sub", event="Event", template="tech"
        )
        assert meta.title == "Test"
        assert meta.template == "tech"

    def test_templateのデフォルト値はtech(self):
        meta = SlideMetadata(title="T", subtitle="S", event="E")
        assert meta.template == "tech"

    def test_無効なtemplateはValueError(self):
        with pytest.raises(ValueError, match="template"):
            SlideMetadata(
                title="T", subtitle="S", event="E", template="invalid"
            )


class TestSlide:
    """Slideの各レイアウトバリデーション"""

    def test_title_slideレイアウト(self):
        slide = Slide(
            layout="title_slide", title="タイトル", subtitle="サブタイトル"
        )
        assert slide.layout == "title_slide"
        assert slide.title == "タイトル"

    def test_title_and_contentレイアウト(self):
        slide = Slide(
            layout="title_and_content",
            title="見出し",
            body=["項目1", "項目2"],
            note="ノート",
        )
        assert slide.body == ["項目1", "項目2"]
        assert slide.note == "ノート"

    def test_two_contentレイアウト(self):
        slide = Slide(
            layout="two_content",
            title="比較",
            left=TwoColumnContent(heading="左", body=["a"]),
            right=TwoColumnContent(heading="右", body=["b"]),
        )
        assert slide.left.heading == "左"
        assert slide.right.body == ["b"]

    def test_無効なlayoutはValueError(self):
        with pytest.raises(ValueError, match="layout"):
            Slide(layout="unknown_layout", title="T")

    def test_noteはオプショナル(self):
        slide = Slide(layout="section_header", title="セクション")
        assert slide.note is None

    def test_bodyはオプショナル(self):
        slide = Slide(layout="title_and_content", title="T")
        assert slide.body is None


class TestValidateSlideSpec:
    """validate_slide_spec() のバリデーション"""

    def test_有効な仕様はSlideSpecを返す(self, valid_spec_dict: dict):
        spec = validate_slide_spec(valid_spec_dict)
        assert isinstance(spec, SlideSpec)
        assert spec.metadata.title == "Claude Codeで変わる開発体験"
        assert len(spec.slides) == 5

    def test_metadataが欠損するとValueError(self):
        with pytest.raises(ValueError, match="metadata"):
            validate_slide_spec({"slides": []})

    def test_slidesが欠損するとValueError(self):
        with pytest.raises(ValueError, match="slides"):
            validate_slide_spec(
                {"metadata": {"title": "T", "subtitle": "S", "event": "E"}}
            )

    def test_slidesが空リストでも有効(self):
        spec = validate_slide_spec(
            {
                "metadata": {
                    "title": "T",
                    "subtitle": "S",
                    "event": "E",
                },
                "slides": [],
            }
        )
        assert len(spec.slides) == 0

    def test_各レイアウトが正しくパースされる(self, valid_spec_dict: dict):
        spec = validate_slide_spec(valid_spec_dict)
        layouts = [s.layout for s in spec.slides]
        assert layouts == [
            "title_slide",
            "section_header",
            "title_and_content",
            "two_content",
            "title_only",
        ]


class TestSaveLoadSlideSpec:
    """JSON保存・読み込み"""

    def test_保存と読み込みのラウンドトリップ(
        self, valid_spec_dict: dict, tmp_output_dir: Path
    ):
        path = tmp_output_dir / "spec.json"
        spec = validate_slide_spec(valid_spec_dict)
        save_slide_spec(spec, path)

        loaded = load_slide_spec(path)
        assert loaded.metadata.title == spec.metadata.title
        assert len(loaded.slides) == len(spec.slides)

    def test_JSONファイルがUTF8で保存される(
        self, valid_spec_dict: dict, tmp_output_dir: Path
    ):
        path = tmp_output_dir / "spec.json"
        spec = validate_slide_spec(valid_spec_dict)
        save_slide_spec(spec, path)

        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["metadata"]["title"] == "Claude Codeで変わる開発体験"

    def test_存在しないファイルはFileNotFoundError(self, tmp_output_dir: Path):
        with pytest.raises(FileNotFoundError):
            load_slide_spec(tmp_output_dir / "nonexistent.json")

    def test_不正なJSONはValueError(self, tmp_output_dir: Path):
        path = tmp_output_dir / "bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ValueError):
            load_slide_spec(path)
