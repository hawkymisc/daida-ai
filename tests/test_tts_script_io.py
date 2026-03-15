"""TDD: TTS Script Export/Import テスト

スピーカーノートをテキストファイルにエクスポートし、
ユーザーが読みを修正した後にインポートする機能を検証する。
"""

import pytest
from pathlib import Path

from daida_ai.lib.talk_script import export_tts_script, load_tts_script


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

DELIMITER_PATTERN = "--- Slide {idx:03d} ---"


class Testエクスポート正常系:
    """export_tts_script: ノートリストからスクリプトファイルを生成する"""

    def test_単一スライドのノートがエクスポートされる(self, tmp_output_dir: Path):
        notes = ["こんにちは"]
        out = tmp_output_dir / "script.txt"

        result = export_tts_script(notes, out)

        assert result == out
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "--- Slide 000 ---" in content
        assert "こんにちは" in content

    def test_複数スライドが区切り線で分割される(self, tmp_output_dir: Path):
        notes = ["スライド1", "スライド2", "スライド3"]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_text(encoding="utf-8")
        assert "--- Slide 000 ---" in content
        assert "--- Slide 001 ---" in content
        assert "--- Slide 002 ---" in content

    def test_空ノートスライドも区切り線が出力される(self, tmp_output_dir: Path):
        notes = ["テスト", "", "まとめ"]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_text(encoding="utf-8")
        assert "--- Slide 001 ---" in content

    def test_複数行ノートがそのまま出力される(self, tmp_output_dir: Path):
        notes = ["1行目\n2行目\n3行目"]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_text(encoding="utf-8")
        assert "1行目\n2行目\n3行目" in content

    def test_出力ディレクトリが自動作成される(self, tmp_output_dir: Path):
        notes = ["テスト"]
        out = tmp_output_dir / "nested" / "dir" / "script.txt"

        export_tts_script(notes, out)

        assert out.exists()

    def test_戻り値はPathオブジェクト(self, tmp_output_dir: Path):
        notes = ["テスト"]
        out = tmp_output_dir / "script.txt"

        result = export_tts_script(notes, out)

        assert isinstance(result, Path)
        assert result == out

    def test_UTF8エンコーディングで出力される(self, tmp_output_dir: Path):
        notes = ["日本語テスト🎤", "English test"]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_bytes().decode("utf-8")
        assert "日本語テスト🎤" in content
        assert "English test" in content


class Testエクスポートエッジケース:
    """export_tts_script: 境界値・特殊入力"""

    def test_空リストでもファイルが作成される(self, tmp_output_dir: Path):
        notes = []
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "--- Slide" not in content

    def test_全スライドが空ノートでも出力される(self, tmp_output_dir: Path):
        notes = ["", "", ""]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_text(encoding="utf-8")
        assert content.count("--- Slide") == 3

    def test_100スライド以上でもゼロ埋めで出力される(self, tmp_output_dir: Path):
        notes = [""] * 100 + ["最後のスライド"]
        out = tmp_output_dir / "script.txt"

        export_tts_script(notes, out)

        content = out.read_text(encoding="utf-8")
        assert "--- Slide 100 ---" in content


class Testインポート正常系:
    """load_tts_script: スクリプトファイルからノートリストを復元する"""

    def test_単一スライドのノートが読み込まれる(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\nこんにちは\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes == ["こんにちは"]

    def test_複数スライドが正しく分割される(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\nスライド1\n"
            "--- Slide 001 ---\nスライド2\n"
            "--- Slide 002 ---\nスライド3\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes == ["スライド1", "スライド2", "スライド3"]

    def test_空ノートスライドが空文字列として読み込まれる(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\nテスト\n"
            "--- Slide 001 ---\n"
            "--- Slide 002 ---\nまとめ\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes[0] == "テスト"
        assert notes[1] == ""
        assert notes[2] == "まとめ"

    def test_複数行ノートが復元される(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\n1行目\n2行目\n3行目\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes == ["1行目\n2行目\n3行目"]

    def test_修正済みテキストが反映される(self, tmp_output_dir: Path):
        """ユーザーが読みを修正した場合のシナリオ"""
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\n"
            "こんにちは、今日はせいせいAIについてお話しします。\n"
            "--- Slide 001 ---\n"
            "クロードは素晴らしいAIです。\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes[0] == "こんにちは、今日はせいせいAIについてお話しします。"
        assert notes[1] == "クロードは素晴らしいAIです。"


class Testラウンドトリップ:
    """export → load で元のノートが復元される"""

    def test_基本的なラウンドトリップ(self, tmp_output_dir: Path):
        original = ["スライド1", "スライド2", "スライド3"]
        path = tmp_output_dir / "script.txt"

        export_tts_script(original, path)
        loaded = load_tts_script(path)

        assert loaded == original

    def test_空ノートを含むラウンドトリップ(self, tmp_output_dir: Path):
        original = ["テスト", "", "まとめ"]
        path = tmp_output_dir / "script.txt"

        export_tts_script(original, path)
        loaded = load_tts_script(path)

        assert loaded == original

    def test_複数行ノートのラウンドトリップ(self, tmp_output_dir: Path):
        original = ["1行目\n2行目", "", "A\nB\nC"]
        path = tmp_output_dir / "script.txt"

        export_tts_script(original, path)
        loaded = load_tts_script(path)

        assert loaded == original

    def test_絵文字を含むラウンドトリップ(self, tmp_output_dir: Path):
        original = ["🎤マイク", "🎵音楽"]
        path = tmp_output_dir / "script.txt"

        export_tts_script(original, path)
        loaded = load_tts_script(path)

        assert loaded == original

    def test_空リストのラウンドトリップ(self, tmp_output_dir: Path):
        original = []
        path = tmp_output_dir / "script.txt"

        export_tts_script(original, path)
        loaded = load_tts_script(path)

        assert loaded == original


class Testインポートエッジケース:
    """load_tts_script: 境界値・特殊入力"""

    def test_末尾に余分な改行があっても正常に読み込まれる(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\nテスト\n\n\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes == ["テスト"]

    def test_区切り線の前後に空行があっても正常(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text(
            "--- Slide 000 ---\nスライド1\n\n"
            "--- Slide 001 ---\nスライド2\n",
            encoding="utf-8",
        )

        notes = load_tts_script(script)

        assert notes[0] == "スライド1"
        assert notes[1] == "スライド2"


class Testインポートエラー:
    """load_tts_script: 異常系"""

    def test_ファイルが存在しない場合FileNotFoundError(self, tmp_output_dir: Path):
        with pytest.raises(FileNotFoundError):
            load_tts_script(tmp_output_dir / "nonexistent.txt")

    def test_区切り線がないファイルでValueError(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text("ただのテキスト\n改行あり\n", encoding="utf-8")

        with pytest.raises(ValueError, match="delimiter"):
            load_tts_script(script)

    def test_空ファイルは空リストを返す(self, tmp_output_dir: Path):
        script = tmp_output_dir / "script.txt"
        script.write_text("", encoding="utf-8")

        notes = load_tts_script(script)

        assert notes == []
