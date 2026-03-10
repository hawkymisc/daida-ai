"""TDD: outline_parser.py — Markdownアウトライン解析テスト"""

import pytest
from daida_ai.lib.outline_parser import parse_outline, OutlineSection, Outline


class TestParseOutline:
    """parse_outline() はMarkdown文字列を構造化データに変換する"""

    # === 正常系: 構造の検証 ===

    def test_タイトルを抽出できる(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        assert outline.title == "Claude Codeで変わる開発体験"

    def test_セクション数が正しい(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        assert len(outline.sections) == 4

    def test_セクションのタイトルが正しい(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        expected_titles = [
            "導入: なぜClaude Codeなのか",
            "本題1: 基本機能",
            "本題2: 実践テクニック",
            "まとめ",
        ]
        actual_titles = [s.title for s in outline.sections]
        assert actual_titles == expected_titles

    def test_箇条書きアイテムが正しい(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        first_section = outline.sections[0]
        assert first_section.items == [
            "AIペアプログラミングの進化",
            "従来のコード補完との違い",
            "開発速度の劇的な向上",
        ]

    def test_全セクションのアイテム数が正しい(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        expected_counts = [3, 3, 3, 2]
        actual_counts = [len(s.items) for s in outline.sections]
        assert actual_counts == expected_counts

    # === 正常系: データ型の検証 ===

    def test_戻り値はOutline型である(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        assert isinstance(outline, Outline)

    def test_セクションはOutlineSection型である(self, sample_outline_md: str):
        outline = parse_outline(sample_outline_md)
        for section in outline.sections:
            assert isinstance(section, OutlineSection)

    # === エッジケース ===

    def test_タイトルのみのアウトライン(self, minimal_outline_md: str):
        outline = parse_outline(minimal_outline_md)
        assert outline.title == "タイトルだけのプレゼン"
        assert outline.sections == []

    def test_ネストされた箇条書きはフラットに展開される(
        self, nested_outline_md: str
    ):
        """サブ項目はインデント付きで保持される"""
        outline = parse_outline(nested_outline_md)
        section1 = outline.sections[0]
        assert "項目A" in section1.items
        assert "サブ項目A-1" in section1.items
        assert "サブ項目A-2" in section1.items
        assert "項目B" in section1.items
        assert len(section1.items) == 4

    def test_空文字列はValueErrorを送出する(self):
        with pytest.raises(ValueError, match="アウトラインが空です"):
            parse_outline("")

    def test_タイトルなしはValueErrorを送出する(self):
        md = "## セクションだけ\n- 項目\n"
        with pytest.raises(ValueError, match="タイトル.*見つかりません"):
            parse_outline(md)

    def test_非常に長いタイトルも処理できる(self):
        long_title = "A" * 1000
        md = f"# {long_title}\n"
        outline = parse_outline(md)
        assert outline.title == long_title

    def test_空行が混在しても正しく解析できる(self):
        md = """\
# タイトル

## セクション1

- 項目1

- 項目2

## セクション2
- 項目3
"""
        outline = parse_outline(md)
        assert outline.title == "タイトル"
        assert len(outline.sections) == 2
        assert outline.sections[0].items == ["項目1", "項目2"]
        assert outline.sections[1].items == ["項目3"]

    def test_箇条書きなしのセクションはitems空リスト(self):
        md = """\
# タイトル

## セクション1

## セクション2
- 項目
"""
        outline = parse_outline(md)
        assert outline.sections[0].items == []
        assert outline.sections[1].items == ["項目"]


class TestOutlineSection:
    """OutlineSectionのデータ構造テスト"""

    def test_titleとitemsを持つ(self):
        section = OutlineSection(title="テスト", items=["a", "b"])
        assert section.title == "テスト"
        assert section.items == ["a", "b"]


class TestOutline:
    """Outlineのデータ構造テスト"""

    def test_titleとsectionsを持つ(self):
        sections = [OutlineSection(title="S1", items=["a"])]
        outline = Outline(title="タイトル", sections=sections)
        assert outline.title == "タイトル"
        assert len(outline.sections) == 1

    def test_to_dictで辞書に変換できる(self):
        sections = [OutlineSection(title="S1", items=["a", "b"])]
        outline = Outline(title="T", sections=sections)
        d = outline.to_dict()
        assert d["title"] == "T"
        assert len(d["sections"]) == 1
        assert d["sections"][0]["title"] == "S1"
        assert d["sections"][0]["items"] == ["a", "b"]
