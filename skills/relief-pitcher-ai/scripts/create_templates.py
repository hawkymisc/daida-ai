#!/usr/bin/env python3
"""PPTXテンプレート生成スクリプト

tech / casual / formal の3種類のテンプレートを生成する。
daida_ai.lib.template_builder を使い、テーマカラー・背景色・フォントを設定する。

NOTE: 本番クオリティにはLibreOffice Impressでの追加調整を推奨。
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.template_builder import build_template, TEMPLATE_DESIGNS

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "assets" / "templates"


def main():
    print("=== Creating PPTX templates ===")
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        for name in TEMPLATE_DESIGNS:
            tmp_out = Path(td) / f"{name}.pptx"
            build_template(name, tmp_out)
            dest = TEMPLATE_DIR / f"{name}.pptx"
            shutil.copy2(str(tmp_out), str(dest))
            print(f"  {name}: {dest} ({dest.stat().st_size} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()
