#!/usr/bin/env python3
"""Step4: スピーカーノート → 音声ファイル生成"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.talk_script import read_notes
from daida_ai.lib.tts_engine import get_engine


async def _synthesize_all(
    notes: list[str],
    output_dir: Path,
    engine_name: str,
    voice: str | None,
) -> list[Path]:
    engine = get_engine(engine_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i, note in enumerate(notes):
        if not note.strip():
            results.append(None)
            continue
        output_path = output_dir / f"slide_{i:03d}.mp3"
        await engine.synthesize(note, output_path, voice=voice)
        results.append(output_path)
        print(f"  Slide {i}: {output_path}")

    return results


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

    asyncio.run(
        _synthesize_all(notes, args.output_dir, args.engine, args.voice)
    )
    print("Done.")


if __name__ == "__main__":
    main()
