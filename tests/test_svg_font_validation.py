"""TDD: SVGフォントサイズバリデーションテスト

SVGがPPTXに埋め込まれた際に12pt未満にならないことを検証する。
数式: rendered_pt = f_svg × display_w_emu / (viewBox_w × 12700)
"""

import math
import warnings

import pytest

from daida_ai.lib.svg_convert import (
    validate_svg_font_sizes,
    compute_min_svg_font_size,
    FontSizeViolation,
)


# --- テスト用SVGデータ ---

_SVG_VALID = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="40" font-family="sans-serif">OK</text>
  <text x="100" y="200" font-size="56" font-family="sans-serif">Big</text>
</svg>
"""

_SVG_TOO_SMALL = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="20" font-family="sans-serif">Small</text>
  <text x="100" y="200" font-size="40" font-family="sans-serif">OK</text>
</svg>
"""

_SVG_INLINE_STYLE = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" style="font-size: 16px" font-family="sans-serif">Tiny</text>
</svg>
"""

_SVG_MIXED = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="56" font-family="sans-serif">Heading</text>
  <text x="100" y="200" style="font-size:24px" font-family="sans-serif">Too Small</text>
  <text x="100" y="300" font-size="10" font-family="sans-serif">Way Too Small</text>
</svg>
"""

_SVG_NO_TEXT = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
</svg>
"""

_SVG_NO_FONTSIZE = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-family="sans-serif">No size</text>
</svg>
"""

_SVG_WIDTH_HEIGHT = """\
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900">
  <text x="100" y="100" font-size="30" font-family="sans-serif">Body</text>
</svg>
"""

_SVG_4_3 = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 900">
  <text x="100" y="100" font-size="30" font-family="sans-serif">Body</text>
</svg>
"""


class TestComputeMinSvgFontSize:
    """compute_min_svg_font_size() の数式検証"""

    def test_viewBox_1920x1080_title_onlyの最低フォントは35(self):
        # max_h = 6858000 - 1600200 - 457200 = 4800600
        # display_w = min(11277295, 4800600 * 1920/1080) = 8534400
        # min_font = ceil(152400 * 1920 / 8534400) = ceil(34.3) = 35
        result = compute_min_svg_font_size(1920, 1080, is_blank=False)
        assert result == 35

    def test_viewBox_1920x1080_blankの最低フォントは28(self):
        # max_h = 6858000 - 457200 - 457200 = 5943600
        # display_w = min(11277295, 5943600 * 1920/1080) = 10577067
        # min_font = ceil(152400 * 1920 / 10577067) = ceil(27.7) = 28
        result = compute_min_svg_font_size(1920, 1080, is_blank=True)
        assert result == 28

    def test_viewBox_1200x900_title_onlyの最低フォントは29(self):
        # display_w = min(11277295, 4800600 * 1200/900) = 6400800
        # min_font = ceil(152400 * 1200 / 6400800) = ceil(28.6) = 29
        result = compute_min_svg_font_size(1200, 900, is_blank=False)
        assert result == 29

    def test_viewBox_1200x900_blankの最低フォントは24(self):
        # display_w = min(11277295, 5943600 * 1200/900) = 7924800
        # min_font = ceil(152400 * 1200 / 7924800) = ceil(23.1) = 24
        result = compute_min_svg_font_size(1200, 900, is_blank=True)
        assert result == 24

    def test_カスタムmin_pt_16で計算(self):
        # min_font = ceil(16 * 12700 * 1920 / 8534400) = ceil(45.7) = 46
        result = compute_min_svg_font_size(1920, 1080, is_blank=False, min_pt=16)
        assert result == 46

    def test_カスタムスライドサイズ(self):
        # 4:3 slide (9144000 x 6858000)
        result = compute_min_svg_font_size(
            1920, 1080, is_blank=False,
            slide_w=9144000, slide_h=6858000,
        )
        # max_w = 9144000 - 914400 = 8229600
        # max_h = 6858000 - 1600200 - 457200 = 4800600
        # display_w = min(8229600, 4800600 * 16/9) = min(8229600, 8534400) = 8229600
        # min_font = ceil(152400 * 1920 / 8229600) = ceil(35.6) = 36
        assert result == 36


class TestValidateSvgFontSizes:
    """validate_svg_font_sizes() の統合テスト"""

    def test_全テキストが基準以上なら違反なし(self):
        violations = validate_svg_font_sizes(_SVG_VALID, is_blank=False)
        assert violations == []

    def test_基準未満のテキストで違反が返る(self):
        violations = validate_svg_font_sizes(_SVG_TOO_SMALL, is_blank=False)
        assert len(violations) == 1
        v = violations[0]
        assert v.font_size == 20
        assert v.min_font_size == 35
        assert "Small" in v.text_content

    def test_インラインstyleのfont_sizeも検出される(self):
        violations = validate_svg_font_sizes(_SVG_INLINE_STYLE, is_blank=False)
        assert len(violations) == 1
        assert violations[0].font_size == 16

    def test_複数違反が全て返る(self):
        violations = validate_svg_font_sizes(_SVG_MIXED, is_blank=False)
        assert len(violations) == 2
        sizes = sorted(v.font_size for v in violations)
        assert sizes == [10, 24]

    def test_テキスト要素なしなら違反なし(self):
        violations = validate_svg_font_sizes(_SVG_NO_TEXT, is_blank=False)
        assert violations == []

    def test_font_size未指定のテキストはスキップ(self):
        """font-size属性もstyleもない場合はバリデーション対象外"""
        violations = validate_svg_font_sizes(_SVG_NO_FONTSIZE, is_blank=False)
        assert violations == []

    def test_blankレイアウトでは基準が緩い(self):
        # viewBox 1920x1080: title_only=35, blank=28
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="30" font-family="sans-serif">Border</text>
</svg>
"""
        violations_title = validate_svg_font_sizes(svg, is_blank=False)
        violations_blank = validate_svg_font_sizes(svg, is_blank=True)
        assert len(violations_title) == 1  # 30 < 35
        assert len(violations_blank) == 0  # 30 >= 28

    def test_width_height属性からviewBox相当を推定(self):
        # width=1200, height=900 → viewBox 0 0 1200 900 として扱う
        violations = validate_svg_font_sizes(_SVG_WIDTH_HEIGHT, is_blank=False)
        # min_font = 29, font-size=30 → OK
        assert len(violations) == 0

    def test_4_3_viewBoxで正しく計算(self):
        violations = validate_svg_font_sizes(_SVG_4_3, is_blank=False)
        # min_font = 29, font-size=30 → OK
        assert len(violations) == 0


class TestFontSizeViolation:
    """FontSizeViolation dataclass"""

    def test_str表現に必要な情報が含まれる(self):
        v = FontSizeViolation(
            font_size=20,
            min_font_size=35,
            text_content="Small",
            rendered_pt=9.6,
        )
        s = str(v)
        assert "20" in s
        assert "35" in s
        assert "Small" in s

    def test_rendered_ptの計算が正しい(self):
        v = FontSizeViolation(
            font_size=20,
            min_font_size=35,
            text_content="Small",
            rendered_pt=9.6,
        )
        assert v.rendered_pt == pytest.approx(9.6, abs=0.1)


class TestEdgeCases:
    """エッジケース"""

    def test_viewBox未指定_width_height未指定でも例外にならない(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><text font-size="10">X</text></svg>'
        # viewBoxもwidth/heightもない場合は検証不可 → 空リスト
        violations = validate_svg_font_sizes(svg, is_blank=False)
        assert violations == []

    def test_font_sizeに単位付きの値(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="20px" font-family="sans-serif">Unit</text>
</svg>
"""
        violations = validate_svg_font_sizes(svg, is_blank=False)
        assert len(violations) == 1
        assert violations[0].font_size == 20

    def test_font_sizeが小数値(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100" font-size="35.5" font-family="sans-serif">Float</text>
</svg>
"""
        violations = validate_svg_font_sizes(svg, is_blank=False)
        assert len(violations) == 0  # 35.5 >= 35

    def test_style内にfont_size以外のプロパティがあっても正しく抽出(self):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <text x="100" y="100"
        style="fill: red; font-size: 20px; font-weight: bold"
        font-family="sans-serif">Styled</text>
</svg>
"""
        violations = validate_svg_font_sizes(svg, is_blank=False)
        assert len(violations) == 1
        assert violations[0].font_size == 20
