#!/usr/bin/env python3
"""Step6: スライドショー自動再生設定

PPTXにauto-advance transitionとaudio auto-playを設定し、
スライドショーを開始したら最後まで完全自動で走るようにする。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.slideshow import configure_slideshow


def main():
    parser = argparse.ArgumentParser(
        description="PPTXにスライドショー自動再生設定を追加する"
    )
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument("output", type=Path, help="出力PPTXファイルパス")
    parser.add_argument(
        "--silent-duration",
        type=int,
        default=3000,
        help="音声なしスライドの表示時間（ミリ秒、デフォルト3000）",
    )
    parser.add_argument(
        "--audio-buffer",
        type=int,
        default=1000,
        help="音声再生後の余白（ミリ秒、デフォルト1000）",
    )
    parser.add_argument(
        "--unmeasurable-duration",
        type=int,
        default=30000,
        help="デュレーション計測不能時のフォールバック（ミリ秒、デフォルト30000）",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    configure_slideshow(
        args.input,
        args.output,
        silent_duration_ms=args.silent_duration,
        audio_buffer_ms=args.audio_buffer,
        unmeasurable_duration_ms=args.unmeasurable_duration,
    )
    print(f"Slideshow configured: {args.output}")


if __name__ == "__main__":
    main()
