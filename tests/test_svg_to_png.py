"""TDD: svg_to_png.py — SVG→PNG変換スクリプトのテスト"""

import sys
from pathlib import Path
import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills" / "daida-ai" / "scripts")
)

from svg_to_png import convert_svg_to_png, SVGConversionError


# テスト用SVG
_SIMPLE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
  <rect width="200" height="100" fill="#4A90D9"/>
  <text x="100" y="55" text-anchor="middle" fill="white"
        font-size="16" font-family="sans-serif">Test</text>
</svg>
"""

_MINIMAL_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'


class TestBasicConversion:
    """基本的なSVG→PNG変換"""

    def test_SVGファイルがPNGに変換される(self, tmp_path):
        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_SIMPLE_SVG)
        png_path = tmp_path / "output.png"

        result = convert_svg_to_png(str(svg_path), str(png_path))

        assert Path(result).exists()
        # PNGマジックバイト確認
        data = Path(result).read_bytes()
        assert data[:4] == b"\x89PNG"

    def test_出力ディレクトリが自動作成される(self, tmp_path):
        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)
        png_path = tmp_path / "nested" / "deep" / "output.png"

        result = convert_svg_to_png(str(svg_path), str(png_path))

        assert Path(result).exists()

    def test_戻り値は出力パス(self, tmp_path):
        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)
        png_path = tmp_path / "result.png"

        result = convert_svg_to_png(str(svg_path), str(png_path))

        assert result == str(png_path)


class TestScaleOption:
    """scale パラメータの検証"""

    def test_scale_2で画像サイズが2倍になる(self, tmp_path):
        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)  # 10x10
        png_1x = tmp_path / "1x.png"
        png_2x = tmp_path / "2x.png"

        convert_svg_to_png(str(svg_path), str(png_1x), scale=1)
        convert_svg_to_png(str(svg_path), str(png_2x), scale=2)

        # 2xのファイルが1xより大きい（ピクセル数が増える）
        assert png_2x.stat().st_size > png_1x.stat().st_size

    def test_デフォルトscaleは2(self, tmp_path):
        """スライド用途のため、デフォルトで2x解像度"""
        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)
        png_default = tmp_path / "default.png"
        png_2x = tmp_path / "2x.png"

        convert_svg_to_png(str(svg_path), str(png_default))
        convert_svg_to_png(str(svg_path), str(png_2x), scale=2)

        assert png_default.stat().st_size == png_2x.stat().st_size


class TestErrorHandling:
    """エラーハンドリング"""

    def test_存在しないSVGでSVGConversionError(self):
        with pytest.raises(SVGConversionError, match="not found"):
            convert_svg_to_png("/nonexistent/input.svg", "/tmp/out.png")

    def test_不正なSVGでSVGConversionError(self, tmp_path):
        bad_svg = tmp_path / "bad.svg"
        bad_svg.write_text("this is not svg at all")
        png_path = tmp_path / "out.png"

        with pytest.raises(SVGConversionError):
            convert_svg_to_png(str(bad_svg), str(png_path))

    def test_cairosvg未インストール時のエラーメッセージ(self, tmp_path):
        """cairosvgがない環境ではわかりやすいエラーを出す"""
        import svg_to_png as mod

        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)

        original = mod.cairosvg
        try:
            mod.cairosvg = None
            with pytest.raises(SVGConversionError, match="cairosvg is not installed"):
                convert_svg_to_png(str(svg_path), str(tmp_path / "out.png"))
        finally:
            mod.cairosvg = original


class TestSVGContent:
    """SVGコンテンツのバリエーション"""

    def test_日本語テキストを含むSVG(self, tmp_path):
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <rect width="400" height="200" fill="#2D3748"/>
  <text x="200" y="110" text-anchor="middle" fill="white"
        font-size="24">アーキテクチャ図</text>
</svg>
"""
        svg_path = tmp_path / "japanese.svg"
        svg_path.write_text(svg, encoding="utf-8")
        png_path = tmp_path / "japanese.png"

        result = convert_svg_to_png(str(svg_path), str(png_path))

        assert Path(result).exists()
        assert Path(result).read_bytes()[:4] == b"\x89PNG"

    def test_16_9アスペクト比のSVG(self, tmp_path):
        """スライド全面用の16:9 SVG"""
        svg = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1a1a2e"/>
  <circle cx="960" cy="540" r="200" fill="#e94560"/>
</svg>
"""
        svg_path = tmp_path / "widescreen.svg"
        svg_path.write_text(svg)
        png_path = tmp_path / "widescreen.png"

        result = convert_svg_to_png(str(svg_path), str(png_path))

        assert Path(result).exists()
