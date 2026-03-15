"""SVG → PNG 変換の共通ヘルパー

slide_builder.py と scripts/svg_to_png.py の両方から使用される。
"""

from __future__ import annotations

import logging
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)

try:
    import cairosvg as _cairosvg
except ImportError:
    _cairosvg = None

# inject_japanese_fonts の有効/無効フラグ（テスト用）
_inject_japanese_fonts_enabled = True

# cairosvg/fontconfig が日本語グリフを持つと確認済みのフォントリスト
# 優先順位: macOS (Hiragino) > Windows (Yu Gothic) > Linux (Noto CJK) > fallback
_JP_FONT_FALLBACK = (
    "Hiragino Sans, Hiragino Kaku Gothic ProN, Hiragino Kaku Gothic Pro, "
    "Yu Gothic, Meiryo, Noto Sans CJK JP, Noto Serif CJK JP, "
)

# 既に日本語フォントが含まれていると見なすキーワード
_JP_FONT_KEYWORDS = ("hiragino", "yu gothic", "meiryo", "noto sans cjk", "noto serif cjk")


class SVGConversionError(Exception):
    """SVG変換に失敗した場合の例外"""


# --- PPTX レイアウト定数 (EMU) ---
_DEFAULT_SLIDE_W = 12191695   # 13.333 inches (16:9)
_DEFAULT_SLIDE_H = 6858000    # 7.500 inches
_IMG_MARGIN = 457200          # 左右・下マージン
_IMG_TOP_TITLE = 1600200      # title_only/title_and_content の画像開始位置
_IMG_TOP_BLANK = 457200       # blank レイアウトの画像開始位置
_EMU_PER_PT = 12700           # 1pt = 12700 EMU (OOXML標準)
_DEFAULT_MIN_PT = 12          # 登壇資料の最低フォントサイズ


@dataclass
class FontSizeViolation:
    """フォントサイズ違反の詳細"""
    font_size: float
    min_font_size: int
    text_content: str
    rendered_pt: float

    def __str__(self) -> str:
        return (
            f"font-size={self.font_size}px (→{self.rendered_pt:.1f}pt) "
            f"< min {self.min_font_size}px: \"{self.text_content}\""
        )


def compute_min_svg_font_size(
    viewbox_w: float,
    viewbox_h: float,
    *,
    is_blank: bool = False,
    min_pt: int = _DEFAULT_MIN_PT,
    slide_w: int = _DEFAULT_SLIDE_W,
    slide_h: int = _DEFAULT_SLIDE_H,
) -> int:
    """PPTXで min_pt 以上に表示されるための最低SVGフォントサイズを算出する。

    数式: min_svg_font = ⌈min_pt × 12700 × viewBox_w / display_w_emu⌉

    Raises:
        ValueError: viewbox_w/viewbox_h が 0 以下の場合
    """
    if viewbox_w <= 0 or viewbox_h <= 0:
        raise ValueError(
            f"viewBox dimensions must be positive: {viewbox_w}x{viewbox_h}"
        )
    margin = _IMG_MARGIN
    img_top = _IMG_TOP_BLANK if is_blank else _IMG_TOP_TITLE
    max_w = slide_w - 2 * margin
    max_h = slide_h - img_top - margin
    display_w = min(max_w, max_h * viewbox_w / viewbox_h)
    return math.ceil(min_pt * _EMU_PER_PT * viewbox_w / display_w)


def _parse_font_size(value: str) -> float | None:
    """font-size 属性値から数値を抽出する。'20', '20px', '20.5px' に対応。

    em, rem, pt, % などの単位は非対応（Noneを返す）。
    """
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(px)?", value.strip())
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _extract_font_size_from_style(style: str) -> float | None:
    """inline style 属性から font-size を抽出する。px/unitless のみ対応。

    em, rem, pt, % などの単位は非対応（Noneを返す）。
    """
    m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)\s*([a-z%]*)", style)
    if not m:
        return None
    unit = m.group(2)
    if unit and unit != "px":
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


_SVG_NS = "http://www.w3.org/2000/svg"


def validate_svg_font_sizes(
    svg_content: str,
    *,
    is_blank: bool = False,
    min_pt: int = _DEFAULT_MIN_PT,
    slide_w: int = _DEFAULT_SLIDE_W,
    slide_h: int = _DEFAULT_SLIDE_H,
) -> list[FontSizeViolation]:
    """SVG内のテキスト要素のフォントサイズがPPTX上で min_pt 以上になるか検証する。

    Returns:
        違反のリスト（空なら全テキストがOK）
    """
    try:
        root = ET.fromstring(svg_content)
    except Exception:
        logger.warning("Invalid SVG content, skipping font size validation")
        return []

    # viewBox または width/height から座標系サイズを取得
    viewbox_w, viewbox_h = None, None
    vb = root.get("viewBox")
    if vb:
        parts = vb.split()
        if len(parts) == 4:
            viewbox_w, viewbox_h = float(parts[2]), float(parts[3])

    if viewbox_w is None or viewbox_h is None:
        w_attr = root.get("width")
        h_attr = root.get("height")
        if w_attr and h_attr:
            w_val = _parse_font_size(w_attr)
            h_val = _parse_font_size(h_attr)
            if w_val and h_val:
                viewbox_w, viewbox_h = w_val, h_val

    if viewbox_w is None or viewbox_h is None:
        return []

    min_font = compute_min_svg_font_size(
        viewbox_w, viewbox_h,
        is_blank=is_blank, min_pt=min_pt,
        slide_w=slide_w, slide_h=slide_h,
    )

    # display_w を再計算して rendered_pt 算出に使う
    margin = _IMG_MARGIN
    img_top = _IMG_TOP_BLANK if is_blank else _IMG_TOP_TITLE
    max_w = slide_w - 2 * margin
    max_h = slide_h - img_top - margin
    display_w = min(max_w, max_h * viewbox_w / viewbox_h)

    violations: list[FontSizeViolation] = []

    _TEXT_TAGS = {"text", "tspan", "textPath"}

    for elem in root.iter():
        tag = elem.tag
        if isinstance(tag, str):
            local = tag.split("}")[-1] if "}" in tag else tag
        else:
            continue
        if local not in _TEXT_TAGS:
            continue

        # font-size を取得: 属性 > inline style
        fs = None
        fs_attr = elem.get("font-size")
        if fs_attr:
            fs = _parse_font_size(fs_attr)
        if fs is None:
            style = elem.get("style")
            if style:
                fs = _extract_font_size_from_style(style)
        if fs is None:
            continue

        if fs < min_font:
            text = (elem.text or "").strip()
            rendered_pt = fs * display_w / (viewbox_w * _EMU_PER_PT)
            violations.append(FontSizeViolation(
                font_size=fs,
                min_font_size=min_font,
                text_content=text,
                rendered_pt=round(rendered_pt, 1),
            ))

    return violations


def inject_japanese_fonts(svg_content: str) -> str:
    """SVG内の font-family 属性に日本語フォントのフォールバックを注入する。

    cairosvg/libcairo は font-family="sans-serif" を Noto Sans（CJKグリフなし）に
    解決するため、日本語テキストが豆腐（□）になる。日本語対応フォントを先頭に
    追加することで、fontconfig が正しいフォントを選択できるようにする。

    既に Hiragino / Yu Gothic / Meiryo / Noto CJK が含まれている場合は変更しない。

    対応箇所:
    - font-family="..." 属性 (ダブル/シングルクォート)
    - style="... font-family: ...; ..." インラインスタイル

    非対応（意図的）:
    - <style> ブロック内の @font-face { font-family: ... } — フェース名宣言への
      誤注入を避けるため、<style> ブロックは変更しない。
      このプロジェクトが生成するSVGは <style> ブロックを使わないため問題ない。
    """
    def _needs_injection(families: str) -> bool:
        return not any(kw in families.lower() for kw in _JP_FONT_KEYWORDS)

    def _rewrite_attr(m: re.Match) -> str:
        quote = m.group(1)
        families = m.group(2)
        if not _needs_injection(families):
            return m.group(0)
        return f'font-family={quote}{_JP_FONT_FALLBACK}{families}{quote}'

    def _rewrite_style(m: re.Match) -> str:
        prop_name = m.group(1)
        families = m.group(2).rstrip()
        if not _needs_injection(families):
            return m.group(0)
        return f'{prop_name}{_JP_FONT_FALLBACK}{families}'

    # <style> ブロックを一時的にプレースホルダに退避して正規表現の誤爆を防ぐ
    style_blocks: list[str] = []

    def _stash_style(m: re.Match) -> str:
        style_blocks.append(m.group(0))
        return f'__STYLE_BLOCK_{len(style_blocks) - 1}__'

    result = re.sub(r'<style[^>]*>.*?</style>', _stash_style, svg_content,
                    flags=re.DOTALL | re.IGNORECASE)

    # font-family="..." 属性
    result = re.sub(
        r'font-family=(["\'])([^"\']+)\1',
        _rewrite_attr,
        result,
    )
    # style="... font-family: ...; ..." インラインスタイル
    result = re.sub(
        r'(font-family\s*:\s*)([^;"\'>]+)',
        _rewrite_style,
        result,
    )

    # 退避した <style> ブロックを復元
    for i, block in enumerate(style_blocks):
        result = result.replace(f'__STYLE_BLOCK_{i}__', block)

    return result


def convert_svg_to_png(
    svg_path: str,
    output_path: str | None = None,
    *,
    scale: int = 2,
) -> str:
    """SVGファイルをPNGに変換する。

    Args:
        svg_path: 入力SVGファイルパス
        output_path: 出力PNGファイルパス（Noneの場合は一時ファイルを生成）
        scale: 拡大倍率（デフォルト2x、スライド用途で高解像度）

    Returns:
        出力PNGファイルパス

    Raises:
        SVGConversionError: 変換失敗時
    """
    if _cairosvg is None:
        raise SVGConversionError(
            "cairosvg is not installed. Run: pip install cairosvg"
        )

    path = Path(svg_path)
    if not path.exists():
        raise SVGConversionError(f"SVG file not found: {svg_path}")

    is_temp = output_path is None
    if is_temp:
        # 一時ファイルを原子的に作成（TOCTOU防止）
        fd, output_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        svg_bytes = path.read_bytes()
        if _inject_japanese_fonts_enabled:
            # このプロジェクトが生成するSVGは常にUTF-8。
            # bytestring でフォント注入済みSVGを渡しつつ、url を base URI として
            # 同時指定することで相対パス（<image href="..."> 等）の解決を維持する。
            svg_text = inject_japanese_fonts(svg_bytes.decode("utf-8"))
            svg_bytes = svg_text.encode("utf-8")
        _cairosvg.svg2png(
            bytestring=svg_bytes,
            url=str(path.resolve()),
            write_to=output_path,
            scale=scale,
        )
    except Exception as e:
        if is_temp:
            Path(output_path).unlink(missing_ok=True)
        raise SVGConversionError(f"SVG conversion failed: {e}") from e

    return output_path
