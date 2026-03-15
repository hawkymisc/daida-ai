"""TDD: svg_convert — SVG→PNG変換の共通ヘルパーテスト"""

from pathlib import Path
import pytest

from daida_ai.lib.svg_convert import (
    convert_svg_to_png,
    SVGConversionError,
    inject_japanese_fonts,
)


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

    def test_不正SVGの一時ファイル変換失敗時にリークしない(self, tmp_path):
        """output_path=Noneで一時ファイル生成後、変換失敗時に削除される"""
        import glob

        bad_svg = tmp_path / "bad.svg"
        bad_svg.write_text("not svg")

        before = set(glob.glob("/tmp/tmp*.png"))
        with pytest.raises(SVGConversionError):
            convert_svg_to_png(str(bad_svg))
        after = set(glob.glob("/tmp/tmp*.png"))

        leaked = after - before
        assert len(leaked) == 0, f"Temp files leaked: {leaked}"

    def test_cairosvg未インストール時のエラーメッセージ(self, tmp_path):
        """cairosvgがない環境ではわかりやすいエラーを出す"""
        import daida_ai.lib.svg_convert as mod

        svg_path = tmp_path / "input.svg"
        svg_path.write_text(_MINIMAL_SVG)

        original = mod._cairosvg
        try:
            mod._cairosvg = None
            with pytest.raises(SVGConversionError, match="cairosvg is not installed"):
                convert_svg_to_png(str(svg_path), str(tmp_path / "out.png"))
        finally:
            mod._cairosvg = original


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

    def test_日本語テキストを含むSVGが豆腐にならない(self, tmp_path):
        """font-family="sans-serif"のSVGでも日本語フォントが自動注入されて豆腐にならない。

        豆腐判定: sans-serif のみで変換した PNG と比較して画素が異なることを確認する。
        (sans-serif → Noto Sans → CJKグリフなし → 豆腐 が既知の状態)
        """
        from PIL import Image

        svg_sans = """\
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <rect width="400" height="200" fill="#1E293B"/>
  <text x="200" y="110" text-anchor="middle" fill="white"
        font-size="40" font-family="sans-serif">日本語テスト</text>
</svg>
"""
        svg_japanese = """\
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <rect width="400" height="200" fill="#1E293B"/>
  <text x="200" y="110" text-anchor="middle" fill="white"
        font-size="40" font-family="sans-serif">日本語テスト</text>
</svg>
"""
        # 修正前: font-family="sans-serif" のみ (豆腐の基準)
        svg_tofu_path = tmp_path / "tofu.svg"
        svg_tofu_path.write_text(svg_sans, encoding="utf-8")
        png_tofu = tmp_path / "tofu.png"

        import daida_ai.lib.svg_convert as mod
        original = mod._inject_japanese_fonts_enabled
        try:
            mod._inject_japanese_fonts_enabled = False
            convert_svg_to_png(str(svg_tofu_path), str(png_tofu))
        finally:
            mod._inject_japanese_fonts_enabled = original

        # 修正後: inject_japanese_fonts が適用された状態
        svg_fixed_path = tmp_path / "fixed.svg"
        svg_fixed_path.write_text(svg_japanese, encoding="utf-8")
        png_fixed = tmp_path / "fixed.png"
        convert_svg_to_png(str(svg_fixed_path), str(png_fixed))

        # 豆腐PNGと修正後PNGは異なるはず
        tofu_data = list(Image.open(png_tofu).convert("RGB").getdata())
        fixed_data = list(Image.open(png_fixed).convert("RGB").getdata())
        assert tofu_data != fixed_data, "日本語フォントが注入されず豆腐になっています"

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


class TestInjectJapaneseFonts:
    """inject_japanese_fonts — font-family への日本語フォント自動注入"""

    def test_sans_serifに日本語フォントが先頭に注入される(self):
        svg = '<text font-family="sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert result.startswith('<text font-family="') or 'font-family=' in result
        assert "Hiragino" in result
        assert "sans-serif" in result

    def test_注入後もsans_serifが末尾に残る(self):
        svg = '<text font-family="sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        # sans-serif はフォールバックとして末尾に残すべき
        families = result.split('font-family="')[1].split('"')[0]
        assert families.strip().endswith("sans-serif")

    def test_既にHiraginoが含まれている場合は変更しない(self):
        svg = '<text font-family="Hiragino Sans, sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert result == svg

    def test_既にYu_Gothicが含まれている場合は変更しない(self):
        svg = '<text font-family="Yu Gothic, sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert result == svg

    def test_既にNoto_Sans_CJKが含まれている場合は変更しない(self):
        svg = '<text font-family="Noto Sans CJK JP, sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert result == svg

    def test_font_familyなしの要素は変更しない(self):
        svg = '<text>テスト</text>'
        result = inject_japanese_fonts(svg)
        assert result == svg

    def test_inline_styleのfont_familyにも注入される(self):
        svg = '<text style="font-size:40px; font-family: sans-serif;">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert "Hiragino" in result

    def test_複数のtext要素すべてに注入される(self):
        svg = (
            '<text font-family="sans-serif">A</text>'
            '<text font-family="sans-serif">B</text>'
        )
        result = inject_japanese_fonts(svg)
        # 元の font-family="sans-serif" がそのまま残っていないこと（両方注入済み）
        assert result.count('font-family="sans-serif"') == 0
        assert "Hiragino" in result

    def test_シングルクォートのfont_familyにも注入される(self):
        svg = "<text font-family='sans-serif'>テスト</text>"
        result = inject_japanese_fonts(svg)
        assert "Hiragino" in result

    def test_欧文のみのfont_familyにも注入される(self):
        """欧文フォント指定でも注入する（日本語が混入するSVGに対応）"""
        svg = '<text font-family="Arial, sans-serif">テスト</text>'
        result = inject_japanese_fonts(svg)
        assert "Hiragino" in result
