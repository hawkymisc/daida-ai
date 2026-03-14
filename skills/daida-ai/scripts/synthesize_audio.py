#!/usr/bin/env python3
"""Step4: スピーカーノート → 音声ファイル生成"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.talk_script import read_notes
from daida_ai.lib.synthesize import synthesize_notes


def main():
    parser = argparse.ArgumentParser(description="スピーカーノートから音声を生成する")
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument("output_dir", type=Path, help="音声ファイル出力ディレクトリ")
    parser.add_argument(
        "--engine",
        choices=["edge", "voicevox"],
        default="edge",
        help="TTSエンジン (default: edge)",
    )
    parser.add_argument("--voice", type=str, default=None, help="音声名/ID")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    notes = read_notes(args.input)
    non_empty = sum(1 for n in notes if n.strip())
    print(f"Synthesizing {non_empty} slides with {args.engine}...")

    results = asyncio.run(
        synthesize_notes(
            notes, args.output_dir, engine_name=args.engine, voice=args.voice
        )
    )
    generated = sum(1 for r in results if r is not None)
    failed = non_empty - generated
    print(f"Generated {generated} audio files.")
    if failed > 0:
        print(
            f"Warning: {failed} slide(s) failed TTS synthesis. "
            f"Re-run Step 4 after resolving the TTS issue.",
            file=sys.stderr,
        )
    print("Done.")


if __name__ == "__main__":
    main()
