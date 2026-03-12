"""SVG → PNG 変換の共通ヘルパー

slide_builder.py と scripts/svg_to_png.py の両方から使用される。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

try:
    import cairosvg as _cairosvg
except ImportError:
    _cairosvg = None


class SVGConversionError(Exception):
    """SVG変換に失敗した場合の例外"""


def convert_svg_to_png(
    svg_path: str,
    output_path: str | None = None,
    *,
    scale: int = 2,
) -> str:
    """SVGファイルをPNGに変換する。

    Args:
        svg_path: 入力SVGファイルパス
        output_path: 出力PNGファイルパス（Noneの場合は一時ファイルを生成）
        scale: 拡大倍率（デフォルト2x、スライド用途で高解像度）

    Returns:
        出力PNGファイルパス

    Raises:
        SVGConversionError: 変換失敗時
    """
    if _cairosvg is None:
        raise SVGConversionError(
            "cairosvg is not installed. Run: pip install cairosvg"
        )

    path = Path(svg_path)
    if not path.exists():
        raise SVGConversionError(f"SVG file not found: {svg_path}")

    if output_path is None:
        # 一時ファイルを原子的に作成（TOCTOU防止）
        fd, output_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        _cairosvg.svg2png(
            url=str(path.resolve()),
            write_to=output_path,
            scale=scale,
        )
    except Exception as e:
        raise SVGConversionError(f"SVG conversion failed: {e}") from e

    return output_path
