#!/usr/bin/env python3
"""Step2: スライド仕様JSON → PPTX生成"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from daida_ai.lib.slide_spec import load_slide_spec
from daida_ai.lib.slide_builder import build_presentation


def main():
    parser = argparse.ArgumentParser(description="スライド仕様JSONからPPTXを生成する")
    parser.add_argument("input", type=Path, help="スライド仕様JSONファイルパス")
    parser.add_argument("output", type=Path, help="出力PPTXファイルパス")
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="カスタムテンプレートPPTXのパス",
    )
    args = parser.parse_args()

    try:
        spec = load_slide_spec(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    template = str(args.template) if args.template else None
    prs = build_presentation(spec, template_path=template)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(args.output))
    print(f"PPTX saved: {args.output} ({len(spec.slides)} slides)")


if __name__ == "__main__":
    main()
