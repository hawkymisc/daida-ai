#!/usr/bin/env python3
"""Step4準備: スピーカーノートをTTSスクリプトファイルにエクスポートする

ユーザーが読み上げテキストを確認・修正できるよう、
区切り線ベースのプレーンテキスト形式で出力する。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.talk_script import read_notes, export_tts_script


def main():
    parser = argparse.ArgumentParser(
        description="スピーカーノートをTTSスクリプトファイルにエクスポートする"
    )
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument("output", type=Path, help="スクリプトファイル出力パス")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    notes = read_notes(args.input)
    non_empty = sum(1 for n in notes if n.strip())
    print(f"Found {len(notes)} slides ({non_empty} with notes).")

    export_tts_script(notes, args.output)
    print(f"Exported TTS script to: {args.output}")
    print("Edit the file to fix pronunciation, then run synthesize_audio.py with --script option.")
    print("Done.")


if __name__ == "__main__":
    main()
