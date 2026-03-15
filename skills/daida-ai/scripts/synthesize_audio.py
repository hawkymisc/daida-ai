#!/usr/bin/env python3
"""Step4: スピーカーノート → 音声ファイル生成"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.talk_script import read_notes, load_tts_script
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
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="TTSスクリプトファイル（指定時はPPTXノートの代わりに使用）",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    pptx_notes = read_notes(args.input)
    if args.script is not None:
        if not args.script.exists():
            print(f"Error: Script file not found: {args.script}", file=sys.stderr)
            sys.exit(1)
        notes = load_tts_script(args.script)
        if len(notes) != len(pptx_notes):
            print(
                f"Error: Script has {len(notes)} slide(s) but PPTX has "
                f"{len(pptx_notes)}. Re-export the script and try again.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Using TTS script: {args.script}")
    else:
        notes = pptx_notes
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
