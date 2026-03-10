#!/usr/bin/env python3
"""Step5: 音声ファイル → PPTX埋め込み"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.audio_embed import embed_audio_to_pptx


def main():
    parser = argparse.ArgumentParser(description="音声ファイルをPPTXに埋め込む")
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument("audio_dir", type=Path, help="音声ファイルディレクトリ")
    parser.add_argument("output", type=Path, help="出力PPTXファイルパス")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.audio_dir.exists():
        print(f"Error: Directory not found: {args.audio_dir}", file=sys.stderr)
        sys.exit(1)

    count = embed_audio_to_pptx(args.input, args.audio_dir, args.output)
    print(f"Embedded {count} audio files: {args.output}")


if __name__ == "__main__":
    main()
