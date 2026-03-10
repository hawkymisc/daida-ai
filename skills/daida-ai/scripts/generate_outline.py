#!/usr/bin/env python3
"""Step1: テーマ → Markdownアウトライン生成・保存

LLM（Claude）が生成したMarkdownアウトラインを受け取り、ファイルに保存する。
アウトラインの生成自体はClaude (SKILL.md) が担当する。
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="アウトラインMarkdownを保存する")
    parser.add_argument("output", type=Path, help="出力ファイルパス (.md)")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="標準入力からMarkdownを読み込む",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="入力ファイルからMarkdownを読み込む",
    )
    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
    elif args.input:
        content = args.input.read_text(encoding="utf-8")
    else:
        print("Error: --stdin or --input required", file=sys.stderr)
        sys.exit(1)

    if not content.strip():
        print("Error: empty outline", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Outline saved: {args.output}")


if __name__ == "__main__":
    main()
