#!/usr/bin/env python3
"""PPTX → ODP変換（LibreOffice headlessモード使用）"""

import argparse
import subprocess
import sys
from pathlib import Path


def convert_pptx_to_odp(input_path: Path, output_dir: Path) -> Path:
    """LibreOffice headlessモードでPPTXをODPに変換する。

    Args:
        input_path: 入力PPTXファイルパス
        output_dir: 出力ディレクトリ

    Returns:
        生成されたODPファイルのパス

    Raises:
        FileNotFoundError: 入力ファイルまたはLibreOfficeが見つからない
        RuntimeError: 変換に失敗
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "odp",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "LibreOffice is not installed. Install with: sudo apt install libreoffice"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed:\n{result.stderr}"
        )

    odp_path = output_dir / input_path.with_suffix(".odp").name
    if not odp_path.exists():
        raise RuntimeError(f"Expected output not found: {odp_path}")

    return odp_path


def main():
    parser = argparse.ArgumentParser(description="PPTXをODPに変換する")
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="出力ディレクトリ（デフォルト: 入力ファイルと同じ場所）",
    )
    args = parser.parse_args()

    output_dir = args.outdir or args.input.parent
    odp_path = convert_pptx_to_odp(args.input, output_dir)
    print(f"Converted: {odp_path}")


if __name__ == "__main__":
    main()
