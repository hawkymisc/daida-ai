#!/usr/bin/env python3
"""SVG → PNG 変換スクリプト

GEMINI_API_KEY がない環境で Claude が生成した SVG を
PPTX 挿入用の PNG に変換する。

Usage:
    python svg_to_png.py input.svg output.png [--scale 2]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

try:
    import cairosvg
except ImportError:
    cairosvg = None


class SVGConversionError(Exception):
    """SVG変換に失敗した場合の例外"""


def convert_svg_to_png(
    svg_path: str,
    output_path: str,
    *,
    scale: int = 2,
) -> str:
    """SVGファイルをPNGに変換する。

    Args:
        svg_path: 入力SVGファイルパス
        output_path: 出力PNGファイルパス
        scale: 拡大倍率（デフォルト2x、スライド用途で高解像度）

    Returns:
        出力PNGファイルパス

    Raises:
        SVGConversionError: 変換失敗時
    """
    if cairosvg is None:
        raise SVGConversionError(
            "cairosvg is not installed. Run: pip install cairosvg"
        )

    path = Path(svg_path)
    if not path.exists():
        raise SVGConversionError(f"SVG file not found: {svg_path}")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        cairosvg.svg2png(
            url=str(path.resolve()),
            write_to=str(out),
            scale=scale,
        )
    except Exception as e:
        raise SVGConversionError(f"SVG conversion failed: {e}") from e

    return str(out)


def main():
    parser = argparse.ArgumentParser(description="SVG → PNG 変換")
    parser.add_argument("input", type=Path, help="入力SVGファイルパス")
    parser.add_argument("output", type=Path, help="出力PNGファイルパス")
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="拡大倍率（デフォルト: 2）",
    )
    args = parser.parse_args()

    try:
        result = convert_svg_to_png(str(args.input), str(args.output), scale=args.scale)
        print(f"PNG saved: {result}")
    except SVGConversionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
