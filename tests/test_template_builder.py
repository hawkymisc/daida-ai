"""TDD: template_builder.py — テンプレートデザイン生成テスト

tech/casual/formal テンプレートが正しい背景色・カラースキーム・フォントを持つか検証する。
"""

import pytest
import zipfile
from pathlib import Path
from lxml import etree

from daida_ai.lib.template_builder import build_template, TEMPLATE_DESIGNS

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_nsmap = {"a": _A_NS, "p": _P_NS}


def _read_theme_xml(pptx_path: Path) -> etree._Element:
    with zipfile.ZipFile(str(pptx_path)) as zf:
        return etree.fromstring(zf.read("ppt/theme/theme1.xml"))


def _read_master_xml(pptx_path: Path) -> etree._Element:
    with zipfile.ZipFile(str(pptx_path)) as zf:
        return etree.fromstring(zf.read("ppt/slideMasters/slideMaster1.xml"))


def _get_color_scheme_value(theme_root, slot_name: str) -> str:
    """カラースキームのスロット値をRGB文字列で返す"""
    clr_scheme = theme_root.find(".//a:clrScheme", _nsmap)
    slot = clr_scheme.find(f"a:{slot_name}", _nsmap)
    srgb = slot.find("a:srgbClr", _nsmap)
    if srgb is not None:
        return srgb.get("val").upper()
    sys_clr = slot.find("a:sysClr", _nsmap)
    if sys_clr is not None:
        return sys_clr.get("lastClr", "").upper()
    return ""


class Testデザイン定義:
    """TEMPLATE_DESIGNSの定義が正しい"""

    def test_3テンプレートが定義されている(self):
        assert set(TEMPLATE_DESIGNS.keys()) == {"tech", "casual", "formal"}

    def test_各テンプレートに必須キーがある(self):
        required = {"bg_color", "dk1", "lt1", "accent1", "accent2",
                    "major_font_latin", "minor_font_latin"}
        for name, design in TEMPLATE_DESIGNS.items():
            for key in required:
                assert key in design, f"{name} missing {key}"


class Testテンプレート生成:
    """build_template()でPPTXファイルが正しく生成される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def generated_template(self, request, tmp_output_dir: Path) -> tuple[str, Path]:
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        return name, output

    def test_ファイルが生成される(self, generated_template):
        _, path = generated_template
        assert path.exists()
        assert path.stat().st_size > 0

    def test_有効なPPTXファイルである(self, generated_template):
        from pptx import Presentation
        _, path = generated_template
        prs = Presentation(str(path))
        assert len(prs.slide_masters) >= 1

    def test_レイアウトが保持される(self, generated_template):
        from pptx import Presentation
        _, path = generated_template
        prs = Presentation(str(path))
        layouts = prs.slide_masters[0].slide_layouts
        layout_names = [l.name for l in layouts]
        assert "Title Slide" in layout_names
        assert "Title and Content" in layout_names
        assert "Section Header" in layout_names
        assert "Two Content" in layout_names


class Test背景色:
    """各テンプレートの背景色が正しい"""

    def test_techは暗い背景(self, tmp_output_dir: Path):
        output = tmp_output_dir / "tech.pptx"
        build_template("tech", output)
        master = _read_master_xml(output)
        bg = master.find(".//p:cSld/p:bg/p:bgPr/a:solidFill/a:srgbClr", _nsmap)
        assert bg is not None, "tech should have solidFill background"
        assert bg.get("val").upper() == TEMPLATE_DESIGNS["tech"]["bg_color"].upper()

    def test_casualは明るい背景(self, tmp_output_dir: Path):
        output = tmp_output_dir / "casual.pptx"
        build_template("casual", output)
        master = _read_master_xml(output)
        bg = master.find(".//p:cSld/p:bg/p:bgPr/a:solidFill/a:srgbClr", _nsmap)
        assert bg is not None
        assert bg.get("val").upper() == TEMPLATE_DESIGNS["casual"]["bg_color"].upper()

    def test_formalは白背景(self, tmp_output_dir: Path):
        output = tmp_output_dir / "formal.pptx"
        build_template("formal", output)
        master = _read_master_xml(output)
        bg = master.find(".//p:cSld/p:bg/p:bgPr/a:solidFill/a:srgbClr", _nsmap)
        assert bg is not None
        assert bg.get("val").upper() == TEMPLATE_DESIGNS["formal"]["bg_color"].upper()


class Testカラースキーム:
    """テーマのカラースキームが正しく設定される"""

    _COLOR_SLOTS = [
        "dk1", "lt1", "dk2", "lt2",
        "accent1", "accent2", "accent3", "accent4",
        "accent5", "accent6", "hlink", "folHlink",
    ]

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_theme(self, request, tmp_output_dir: Path):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        theme = _read_theme_xml(output)
        return name, theme

    def test_全カラースロットがデザイン通り設定される(self, template_theme):
        name, theme = template_theme
        design = TEMPLATE_DESIGNS[name]
        for slot in self._COLOR_SLOTS:
            actual = _get_color_scheme_value(theme, slot)
            expected = design[slot].upper()
            assert actual == expected, \
                f"{name}.{slot}: expected {expected}, got {actual}"

    def test_カラースキーム名が設定される(self, template_theme):
        name, theme = template_theme
        clr_scheme = theme.find(".//a:clrScheme", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["color_scheme_name"]
        assert clr_scheme.get("name") == expected


class Testフォント:
    """テーマのフォントスキームが正しく設定される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_theme(self, request, tmp_output_dir: Path):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        theme = _read_theme_xml(output)
        return name, theme

    def test_majorFont_latinが設定される(self, template_theme):
        name, theme = template_theme
        latin = theme.find(".//a:fontScheme/a:majorFont/a:latin", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["major_font_latin"]
        assert latin.get("typeface") == expected

    def test_minorFont_latinが設定される(self, template_theme):
        name, theme = template_theme
        latin = theme.find(".//a:fontScheme/a:minorFont/a:latin", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["minor_font_latin"]
        assert latin.get("typeface") == expected

    def test_majorFont_jpanが設定される(self, template_theme):
        name, theme = template_theme
        jpan = theme.find(
            ".//a:fontScheme/a:majorFont/a:font[@script='Jpan']", _nsmap
        )
        expected = TEMPLATE_DESIGNS[name]["major_font_jpan"]
        assert jpan.get("typeface") == expected

    def test_minorFont_jpanが設定される(self, template_theme):
        name, theme = template_theme
        jpan = theme.find(
            ".//a:fontScheme/a:minorFont/a:font[@script='Jpan']", _nsmap
        )
        expected = TEMPLATE_DESIGNS[name]["minor_font_jpan"]
        assert jpan.get("typeface") == expected

    def test_テーマ名が設定される(self, template_theme):
        name, theme = template_theme
        expected = TEMPLATE_DESIGNS[name]["theme_name"]
        assert theme.get("name") == expected


class Test差別化:
    """3テンプレートが互いに異なることを検証"""

    def test_背景色が全て異なる(self):
        bg_colors = {d["bg_color"] for d in TEMPLATE_DESIGNS.values()}
        assert len(bg_colors) == 3

    def test_accent1が全て異なる(self):
        accents = {d["accent1"] for d in TEMPLATE_DESIGNS.values()}
        assert len(accents) == 3

    def test_不正なテンプレート名はValueError(self):
        with pytest.raises(ValueError, match="Unknown template"):
            build_template("invalid", Path("/tmp/test.pptx"))
