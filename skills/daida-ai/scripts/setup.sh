#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "=== daida-ai setup ==="
echo "Project root: $PROJECT_ROOT"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$PROJECT_ROOT[voicevox,svg]"

echo ""
echo "=== Base setup complete ==="

# ---------------------------------------------------------------------------
# Video generation tools (optional)
# ---------------------------------------------------------------------------
echo ""
echo "--- 動画生成オプション ---"
echo "MP4動画の生成には追加ツール（LibreOffice, ffmpeg, pdftoppm）が必要です。"
echo ""

# Check current availability
LO_OK=false
FFMPEG_OK=false
PDFTOPPM_OK=false

if command -v libreoffice &>/dev/null; then
    LO_OK=true
    echo "  [OK] LibreOffice: $(libreoffice --version 2>/dev/null | head -1)"
else
    echo "  [--] LibreOffice: 未インストール"
fi

if command -v ffmpeg &>/dev/null; then
    FFMPEG_OK=true
    echo "  [OK] ffmpeg: $(ffmpeg -version 2>/dev/null | head -1)"
else
    echo "  [--] ffmpeg: 未インストール"
fi

if command -v pdftoppm &>/dev/null; then
    PDFTOPPM_OK=true
    echo "  [OK] pdftoppm: インストール済み"
else
    echo "  [--] pdftoppm: 未インストール (ffmpegで代替可能)"
fi

echo ""

if $LO_OK && $FFMPEG_OK; then
    echo "動画生成に必要なツールは全てインストール済みです。"
    echo "Step 7（make_video.py）が利用可能です。"
else
    echo "動画生成を利用するには、以下のコマンドで追加ツールをインストールしてください:"
    echo ""
    if ! $LO_OK; then
        echo "  # LibreOffice (PPTX→PDF→PNG変換)"
        echo "  sudo apt install libreoffice        # Ubuntu/Debian"
        echo "  brew install libreoffice             # macOS"
        echo ""
    fi
    if ! $FFMPEG_OK; then
        echo "  # ffmpeg (動画合成)"
        echo "  sudo apt install ffmpeg              # Ubuntu/Debian"
        echo "  brew install ffmpeg                  # macOS"
        echo ""
    fi
    if ! $PDFTOPPM_OK; then
        echo "  # pdftoppm (PDF→PNG、推奨だがffmpegで代替可能)"
        echo "  sudo apt install poppler-utils       # Ubuntu/Debian"
        echo "  brew install poppler                 # macOS"
        echo ""
    fi
    echo "動画生成が不要であればスキップしてOKです。"
fi

echo ""
echo "=== Setup complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
