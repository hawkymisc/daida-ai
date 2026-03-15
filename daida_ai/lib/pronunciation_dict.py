"""TTS読み辞書のロードとテキスト置換

TSV形式の辞書ファイルから置換ペアを読み込み、
テキストに適用する。音声合成前の読み修正に使用。
"""

from __future__ import annotations

from pathlib import Path


def load_dict(dict_path: Path) -> list[tuple[str, str]]:
    """TSV辞書ファイルから置換エントリを読み込む。

    Args:
        dict_path: 辞書ファイルパス（TSV形式）

    Returns:
        [(置換前, 置換後), ...] のリスト（定義順）

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: 不正なフォーマット（タブ区切りでない行）
    """
    if not dict_path.exists():
        raise FileNotFoundError(f"File not found: {dict_path}")

    entries: list[tuple[str, str]] = []
    for lineno, line in enumerate(
        dict_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("\t")
        if len(parts) != 2:
            raise ValueError(
                f"Line {lineno}: expected 2 tab-separated columns, "
                f"got {len(parts)}: {line!r}"
            )
        entries.append((parts[0], parts[1]))
    return entries


def apply_dict(text: str, entries: list[tuple[str, str]]) -> str:
    """辞書エントリに基づきテキスト内の単語を置換する。

    Args:
        text: 置換対象テキスト
        entries: [(置換前, 置換後), ...] のリスト

    Returns:
        置換済みテキスト
    """
    for before, after in entries:
        text = text.replace(before, after)
    return text
