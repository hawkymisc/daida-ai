"""PPTXスピーカーノートの読み書き"""

from __future__ import annotations

from pathlib import Path
from pptx import Presentation


def read_notes(pptx_path: Path) -> list[str]:
    """PPTXファイルから全スライドのスピーカーノートを取得する。

    Returns:
        スライド順のノートテキストリスト（ノートがなければ空文字）

    Raises:
        FileNotFoundError: ファイルが存在しない
    """
    if not pptx_path.exists():
        raise FileNotFoundError(f"File not found: {pptx_path}")

    prs = Presentation(str(pptx_path))
    notes = []
    for slide in prs.slides:
        if slide.has_notes_slide:
            text = slide.notes_slide.notes_text_frame.text
            notes.append(text.strip())
        else:
            notes.append("")
    return notes


def write_notes(
    input_path: Path,
    notes: list[str],
    output_path: Path,
) -> None:
    """PPTXファイルのスピーカーノートを上書きする。

    Args:
        input_path: 入力PPTXファイルパス
        notes: スライド順のノートテキストリスト
        output_path: 出力PPTXファイルパス（input_pathと同一でも可）

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: ノート数とスライド数が一致しない
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    prs = Presentation(str(input_path))

    if len(notes) != len(prs.slides):
        raise ValueError(
            f"スライド数({len(prs.slides)})とノート数({len(notes)})が一致しません"
        )

    for slide, note_text in zip(prs.slides, notes):
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = note_text

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
