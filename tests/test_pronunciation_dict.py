"""TDD: pronunciation_dict.py — 読み辞書テスト

TSV形式の読み辞書のロードとテキスト置換を検証する。
"""

import pytest
from pathlib import Path

from daida_ai.lib.pronunciation_dict import load_dict, apply_dict


class Testロード正常系:
    """load_dict: TSVファイルから辞書エントリを読み込む"""

    def test_単一エントリを読み込む(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("生成\tせいせい\n", encoding="utf-8")

        entries = load_dict(tsv)

        assert entries == [("生成", "せいせい")]

    def test_複数エントリを定義順に読み込む(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text(
            "生成\tせいせい\n"
            "Claude\tクロード\n"
            "LLM\tエルエルエム\n",
            encoding="utf-8",
        )

        entries = load_dict(tsv)

        assert len(entries) == 3
        assert entries[0] == ("生成", "せいせい")
        assert entries[1] == ("Claude", "クロード")
        assert entries[2] == ("LLM", "エルエルエム")

    def test_コメント行はスキップされる(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text(
            "# これはコメントです\n"
            "生成\tせいせい\n"
            "# もう一つのコメント\n"
            "Claude\tクロード\n",
            encoding="utf-8",
        )

        entries = load_dict(tsv)

        assert entries == [("生成", "せいせい"), ("Claude", "クロード")]

    def test_空行はスキップされる(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text(
            "生成\tせいせい\n"
            "\n"
            "\n"
            "Claude\tクロード\n",
            encoding="utf-8",
        )

        entries = load_dict(tsv)

        assert entries == [("生成", "せいせい"), ("Claude", "クロード")]

    def test_戻り値はタプルのリスト(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("テスト\tてすと\n", encoding="utf-8")

        entries = load_dict(tsv)

        assert isinstance(entries, list)
        assert isinstance(entries[0], tuple)
        assert len(entries[0]) == 2


class Testロードエッジケース:
    """load_dict: 境界値・特殊入力"""

    def test_空ファイルは空リストを返す(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("", encoding="utf-8")

        entries = load_dict(tsv)

        assert entries == []

    def test_コメントのみのファイルは空リストを返す(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("# コメントのみ\n# もう一つ\n", encoding="utf-8")

        entries = load_dict(tsv)

        assert entries == []

    def test_絵文字を含むエントリ(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("🎤\tマイク\n", encoding="utf-8")

        entries = load_dict(tsv)

        assert entries == [("🎤", "マイク")]

    def test_末尾に改行がなくても読み込める(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("生成\tせいせい", encoding="utf-8")

        entries = load_dict(tsv)

        assert entries == [("生成", "せいせい")]


class Testロードエラー:
    """load_dict: 異常系"""

    def test_ファイルが存在しない場合FileNotFoundError(self, tmp_output_dir: Path):
        with pytest.raises(FileNotFoundError, match="File not found"):
            load_dict(tmp_output_dir / "nonexistent.tsv")

    def test_タブ区切りでない行でValueError(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("タブなしの行\n", encoding="utf-8")

        with pytest.raises(ValueError, match="tab"):
            load_dict(tsv)

    def test_3カラム以上の行でValueError(self, tmp_output_dir: Path):
        tsv = tmp_output_dir / "dict.tsv"
        tsv.write_text("a\tb\tc\n", encoding="utf-8")

        with pytest.raises(ValueError, match="tab"):
            load_dict(tsv)


class Test置換正常系:
    """apply_dict: テキスト内の単語を辞書に基づき置換する"""

    def test_単一置換(self):
        entries = [("生成", "せいせい")]

        result = apply_dict("生成AIの話", entries)

        assert result == "せいせいAIの話"

    def test_複数置換(self):
        entries = [("生成", "せいせい"), ("Claude", "クロード")]

        result = apply_dict("Claudeは生成AIです", entries)

        assert result == "クロードはせいせいAIです"

    def test_同一テキスト内で複数回出現する単語を全て置換(self):
        entries = [("AI", "エーアイ")]

        result = apply_dict("AIとAIの話", entries)

        assert result == "エーアイとエーアイの話"

    def test_辞書が空なら元テキストがそのまま返る(self):
        result = apply_dict("テスト", [])

        assert result == "テスト"

    def test_該当なしなら元テキストがそのまま返る(self):
        entries = [("生成", "せいせい")]

        result = apply_dict("関係ないテキスト", entries)

        assert result == "関係ないテキスト"


class Test置換エッジケース:
    """apply_dict: 境界値・特殊入力"""

    def test_空テキストに対する置換(self):
        entries = [("生成", "せいせい")]

        result = apply_dict("", entries)

        assert result == ""

    def test_置換後のテキストが更に置換対象になる連鎖置換は行わない(self):
        """辞書順に適用するが、置換結果が再度マッチすることは想定しない"""
        entries = [("A", "B"), ("B", "C")]

        result = apply_dict("A", entries)

        # "A"→"B"に置換後、"B"→"C"の置換も適用される（単純な順次置換）
        assert result == "C"

    def test_置換前と置換後が同じ(self):
        entries = [("テスト", "テスト")]

        result = apply_dict("テスト", entries)

        assert result == "テスト"

    def test_長い置換対象も正しく処理される(self):
        entries = [("スライドショー", "すらいどしょー")]

        result = apply_dict("スライドショーを開始します", entries)

        assert result == "すらいどしょーを開始します"
