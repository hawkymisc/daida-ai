#!/usr/bin/env python3
"""Step3: 既存PPTXのスピーカーノートを更新する"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from daida_ai.lib.talk_script import read_notes, write_notes


def main():
    parser = argparse.ArgumentParser(description="PPTXのスピーカーノートを更新する")
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument(
        "--output", type=Path, default=None, help="出力PPTXファイルパス（省略時は上書き）"
    )
    parser.add_argument(
        "--notes-json",
        type=Path,
        help="ノートテキストのJSONファイル（文字列の配列）",
    )
    parser.add_argument(
        "--read",
        action="store_true",
        help="現在のノートをJSON形式で出力する",
    )
    args = parser.parse_args()

    if args.read:
        notes = read_notes(args.input)
        print(json.dumps(notes, ensure_ascii=False, indent=2))
        return

    if not args.notes_json:
        print("Error: --notes-json or --read required", file=sys.stderr)
        sys.exit(1)

    raw = args.notes_json.read_text(encoding="utf-8")
    notes = json.loads(raw)

    output = args.output or args.input
    write_notes(args.input, notes, output)
    print(f"Notes updated: {output}")


if __name__ == "__main__":
    main()
