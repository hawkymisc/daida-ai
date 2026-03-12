#!/usr/bin/env python3
"""Step2: スライド仕様JSON → PPTX生成"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pptx.exc import PackageNotFoundError

from daida_ai.lib.slide_spec import load_slide_spec
from daida_ai.lib.slide_builder import build_presentation

# 同梱テンプレートのディレクトリ
_BUILTIN_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


def _resolve_template(spec_template: str, cli_template: Path | None) -> str | None:
    """テンプレートパスを解決する。

    優先順位:
    1. CLI引数で明示指定された場合 → そのパス
    2. metadata.templateが同梱テンプレート名の場合 → 同梱テンプレートのパス
    3. いずれにも該当しない場合 → None（python-pptxデフォルト）
    """
    if cli_template:
        return str(cli_template)

    builtin = _BUILTIN_TEMPLATES_DIR / f"{spec_template}.pptx"
    if builtin.exists():
        return str(builtin)

    return None


def main():
    parser = argparse.ArgumentParser(description="スライド仕様JSONからPPTXを生成する")
    parser.add_argument("input", type=Path, help="スライド仕様JSONファイルパス")
    parser.add_argument("output", type=Path, help="出力PPTXファイルパス")
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="カスタムテンプレートPPTXのパス（省略時はmetadata.templateを使用）",
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

    template_path = _resolve_template(spec.metadata.template, args.template)

    try:
        prs = build_presentation(spec, template_path=template_path, base_dir=args.input.parent)
    except (FileNotFoundError, PackageNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(args.output))

    template_name = spec.metadata.template if not args.template else str(args.template)
    print(f"PPTX saved: {args.output} ({len(spec.slides)} slides, template: {template_name})")


if __name__ == "__main__":
    main()
