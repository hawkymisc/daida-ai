"""音声ファイルのPPTX埋め込み"""

from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.opc.package import Part, PackURI, RT


def embed_audio_to_pptx(
    input_path: Path,
    audio_dir: Path,
    output_path: Path,
) -> int:
    """音声ファイルをPPTXの各スライドに埋め込む。

    音声ファイルは slide_000.mp3, slide_001.mp3, ... の命名規則。
    対応するファイルが存在するスライドにのみ埋め込む。

    Args:
        input_path: 入力PPTXファイルパス
        audio_dir: 音声ファイルディレクトリ
        output_path: 出力PPTXファイルパス

    Returns:
        埋め込まれた音声ファイル数
    """
    prs = Presentation(str(input_path))
    count = 0

    for i, slide in enumerate(prs.slides):
        audio_path = audio_dir / f"slide_{i:03d}.mp3"
        if not audio_path.exists():
            continue

        _embed_audio_in_slide(prs, slide, audio_path, i)
        count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return count


def _embed_audio_in_slide(prs, slide, audio_path: Path, slide_idx: int) -> None:
    """単一スライドに音声ファイルを埋め込む。

    python-pptxは音声の直接埋め込みAPIを持たないため、
    OPC パッケージレベルで音声パーツを追加し、スライドから参照する。
    """
    audio_data = audio_path.read_bytes()
    part_name = f"/ppt/media/audio_slide{slide_idx:03d}.mp3"

    audio_part = Part(
        PackURI(part_name),
        "audio/mpeg",
        prs.part.package,
        blob=audio_data,
    )

    slide.part.relate_to(audio_part, RT.MEDIA)
