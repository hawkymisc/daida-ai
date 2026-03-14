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

    def test_slidesが空リストはValueError(self):
        with pytest.raises(ValueError, match="slide"):
            validate_slide_spec(
                {
                    "metadata": {
                        "title": "T",
                        "subtitle": "S",
                        "event": "E",
                    },
                    "slides": [],
                }
            )

    def test_metadata_titleが欠損するとValueError(self):
        with pytest.raises(ValueError, match="title"):
            validate_slide_spec(
                {
                    "metadata": {"subtitle": "S", "event": "E"},
                    "slides": [],
                }
            )

    def test_slideのlayoutが欠損するとValueError(self):
        with pytest.raises(ValueError, match="layout"):
            validate_slide_spec(
                {
                    "metadata": {"title": "T", "subtitle": "S", "event": "E"},
                    "slides": [{"title": "no layout"}],
                }
            )

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


def _make_spec_dict(slides: list[dict], **meta_overrides) -> dict:
    """テスト用のspec辞書を組み立てるヘルパー"""
    meta = {"title": "T", "subtitle": "S", "event": "E"}
    meta.update(meta_overrides)
    return {"metadata": meta, "slides": slides}


class TestA1ガードレール_タイトル非空:
    """A1: すべてのスライドにtitleが非空であること"""

    def test_空タイトルのスライドはValueError(self):
        with pytest.raises(ValueError, match="title"):
            validate_slide_spec(
                _make_spec_dict([{"layout": "title_and_content", "title": ""}])
            )

    def test_titleキー省略時もValueError(self):
        with pytest.raises(ValueError, match="title"):
            validate_slide_spec(
                _make_spec_dict([{"layout": "title_and_content"}])
            )

    def test_空白のみのタイトルはValueError(self):
        with pytest.raises(ValueError, match="title"):
            validate_slide_spec(
                _make_spec_dict([{"layout": "title_and_content", "title": "   "}])
            )

    def test_非空タイトルは通る(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_slide", "title": "表紙", "note": "テスト"},
            ])
        )
        assert spec.slides[0].title == "表紙"

    def test_blankレイアウトはタイトル空でも有効(self):
        """blankはフルスクリーン画像用でタイトル不要"""
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "blank", "note": "テスト"},
            ])
        )
        assert spec.slides[0].title == ""


class TestA1ガードレール_スライド枚数:
    """A1: 1 ≤ len(slides) ≤ max_slides（登壇形式に応じて変動）"""

    def test_スライド0枚はValueError(self):
        with pytest.raises(ValueError, match="slide"):
            validate_slide_spec(_make_spec_dict([]))

    def test_スライド1枚は有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_slide", "title": "表紙", "note": "テスト"},
            ])
        )
        assert len(spec.slides) == 1

    @pytest.mark.parametrize(
        "max_slides, label",
        [
            (20, "5分LT"),
            (40, "15分LT"),
            (60, "30分講演"),
        ],
    )
    def test_上限ちょうどの枚数は有効(self, max_slides, label):
        slides = [
            {"layout": "title_and_content", "title": f"S{i}", "body": ["x"], "note": "テスト"}
            for i in range(max_slides)
        ]
        spec = validate_slide_spec(
            _make_spec_dict(slides), max_slides=max_slides
        )
        assert len(spec.slides) == max_slides

    @pytest.mark.parametrize(
        "max_slides, label",
        [
            (20, "5分LT"),
            (40, "15分LT"),
            (60, "30分講演"),
        ],
    )
    def test_上限超過はValueError(self, max_slides, label):
        slides = [
            {"layout": "title_and_content", "title": f"S{i}", "body": ["x"], "note": "テスト"}
            for i in range(max_slides + 1)
        ]
        with pytest.raises(ValueError, match="slide"):
            validate_slide_spec(
                _make_spec_dict(slides), max_slides=max_slides
            )

    def test_デフォルトは20枚上限(self):
        """max_slides未指定時はMAX_SLIDES=20がデフォルト"""
        slides = [
            {"layout": "title_and_content", "title": f"S{i}", "body": ["x"], "note": "テスト"}
            for i in range(21)
        ]
        with pytest.raises(ValueError, match="20"):
            validate_slide_spec(_make_spec_dict(slides))


class TestA1ガードレール_ノート必須:
    """A1: title_slide, section_header以外のスライドにはnoteが必須"""

    def test_コンテンツスライドにnoteなしはValueError(self):
        with pytest.raises(ValueError, match="note"):
            validate_slide_spec(
                _make_spec_dict([
                    {"layout": "title_slide", "title": "表紙"},
                    {"layout": "title_and_content", "title": "T", "body": ["x"]},
                ])
            )

    def test_コンテンツスライドにnote空文字はValueError(self):
        with pytest.raises(ValueError, match="note"):
            validate_slide_spec(
                _make_spec_dict([
                    {"layout": "title_slide", "title": "表紙"},
                    {"layout": "title_and_content", "title": "T", "body": ["x"], "note": ""},
                ])
            )

    def test_title_slideはnoteなしでも有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_slide", "title": "表紙"},
            ])
        )
        assert spec.slides[0].note is None

    def test_section_headerはnoteなしでも有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "section_header", "title": "セクション"},
            ])
        )
        assert spec.slides[0].note is None


class TestA1ガードレール_情報密度:
    """A1: コンテンツスライドの箇条書き数が1〜8の範囲内"""

    def test_bodyが0項目のコンテンツスライドはValueError(self):
        with pytest.raises(ValueError, match="body"):
            validate_slide_spec(
                _make_spec_dict([
                    {"layout": "title_and_content", "title": "T", "body": [], "note": "テスト"},
                ])
            )

    def test_bodyが9項目のコンテンツスライドはValueError(self):
        with pytest.raises(ValueError, match="body"):
            validate_slide_spec(
                _make_spec_dict([
                    {
                        "layout": "title_and_content",
                        "title": "T",
                        "body": [f"item{i}" for i in range(9)],
                        "note": "テスト",
                    },
                ])
            )

    def test_bodyが1項目は有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_and_content", "title": "T", "body": ["x"], "note": "テスト"},
            ])
        )
        assert len(spec.slides[0].body) == 1

    def test_bodyが8項目は有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {
                    "layout": "title_and_content",
                    "title": "T",
                    "body": [f"item{i}" for i in range(8)],
                    "note": "テスト",
                },
            ])
        )
        assert len(spec.slides[0].body) == 8

    def test_title_slideはbodyチェック対象外(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_slide", "title": "表紙"},
            ])
        )
        assert spec.slides[0].body is None

    def test_bodyがNoneのコンテンツスライドは有効(self):
        """title_onlyなどbodyがないレイアウトは許容"""
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_only", "title": "図", "note": "テスト"},
            ])
        )
        assert spec.slides[0].body is None

    def test_two_contentのleft_bodyが9項目はValueError(self):
        with pytest.raises(ValueError, match="left.body"):
            validate_slide_spec(
                _make_spec_dict([
                    {
                        "layout": "two_content",
                        "title": "比較",
                        "left": {"heading": "左", "body": [f"item{i}" for i in range(9)]},
                        "right": {"heading": "右", "body": ["a"]},
                        "note": "テスト",
                    },
                ])
            )

    def test_two_contentのright_bodyが9項目はValueError(self):
        with pytest.raises(ValueError, match="right.body"):
            validate_slide_spec(
                _make_spec_dict([
                    {
                        "layout": "two_content",
                        "title": "比較",
                        "left": {"heading": "左", "body": ["a"]},
                        "right": {"heading": "右", "body": [f"item{i}" for i in range(9)]},
                        "note": "テスト",
                    },
                ])
            )

    def test_two_contentの各カラム8項目は有効(self):
        spec = validate_slide_spec(
            _make_spec_dict([
                {
                    "layout": "two_content",
                    "title": "比較",
                    "left": {"heading": "左", "body": [f"L{i}" for i in range(8)]},
                    "right": {"heading": "右", "body": [f"R{i}" for i in range(8)]},
                    "note": "テスト",
                },
            ])
        )
        assert len(spec.slides[0].left.body) == 8


class TestA1ガードレール_推定発話時間:
    """A1: 全ノートの合計文字数 / 5.0 ≤ max_talk_duration_sec"""

    @pytest.mark.parametrize(
        "max_sec, label",
        [
            (300, "5分LT"),
            (900, "15分LT"),
            (1800, "30分講演"),
        ],
    )
    def test_上限ちょうどの文字数は有効(self, max_sec, label):
        """max_sec秒 × 5文字/秒 = ちょうど上限"""
        char_count = int(max_sec * 5.0)
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_and_content", "title": "T", "body": ["x"], "note": "あ" * char_count},
            ]),
            max_slides=100,
            max_talk_duration_sec=max_sec,
        )
        assert len(spec.slides) == 1

    @pytest.mark.parametrize(
        "max_sec, label",
        [
            (300, "5分LT"),
            (900, "15分LT"),
            (1800, "30分講演"),
        ],
    )
    def test_上限超過はValueError(self, max_sec, label):
        """max_sec秒を1文字分超過"""
        char_count = int(max_sec * 5.0) + 1
        with pytest.raises(ValueError, match="duration"):
            validate_slide_spec(
                _make_spec_dict([
                    {"layout": "title_and_content", "title": "T", "body": ["x"], "note": "あ" * char_count},
                ]),
                max_slides=100,
                max_talk_duration_sec=max_sec,
            )

    def test_デフォルトは300秒上限(self):
        """max_talk_duration_sec未指定時は300秒がデフォルト"""
        note = "あ" * 1501  # 1501 / 5.0 = 300.2秒
        with pytest.raises(ValueError, match="300"):
            validate_slide_spec(
                _make_spec_dict([
                    {"layout": "title_and_content", "title": "T", "body": ["x"], "note": note},
                ])
            )

    def test_複数スライドのノート合計で判定(self):
        """各スライド750文字 × 2 = 1500文字 = 300秒ちょうど"""
        slides = [
            {"layout": "title_and_content", "title": f"S{i}", "body": ["x"], "note": "あ" * 750}
            for i in range(2)
        ]
        spec = validate_slide_spec(_make_spec_dict(slides))
        assert len(spec.slides) == 2

    def test_ノートなしスライドは発話時間0として計算(self):
        """title_slideのノートなしは0文字として計算される"""
        spec = validate_slide_spec(
            _make_spec_dict([
                {"layout": "title_slide", "title": "表紙"},
                {"layout": "title_and_content", "title": "T", "body": ["x"], "note": "あ" * 100},
            ])
        )
        assert len(spec.slides) == 2
