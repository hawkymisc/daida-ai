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

from daida_ai.lib.svg_convert import convert_svg_to_png, SVGConversionError  # noqa: E402


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
