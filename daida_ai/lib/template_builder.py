"""PPTXテンプレートのデザイン生成

Office デフォルトテンプレートをベースに、テーマカラー・背景色・フォントを
プログラム的に書き換えて tech/casual/formal の3テンプレートを生成する。

python-pptxはテーマ編集APIを持たないため、zipfile + lxml で直接XML操作する。
"""

from __future__ import annotations

import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from lxml import etree

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"

# テンプレートデザイン定義
TEMPLATE_DESIGNS: dict[str, dict[str, str]] = {
    "tech": {
        "bg_color": "1A1A2E",
        "dk1": "E8E8E8",    # メインテキスト（明るいグレー）
        "lt1": "1A1A2E",    # メイン背景
        "dk2": "B0B0B0",    # サブテキスト
        "lt2": "2D2D44",    # サブ背景
        "accent1": "00D4FF",  # シアン
        "accent2": "7B68EE",  # パープル
        "accent3": "00E676",  # グリーン
        "accent4": "FF4081",  # ピンク
        "accent5": "FFD740",  # イエロー
        "accent6": "448AFF",  # ブルー
        "hlink": "00D4FF",
        "folHlink": "7B68EE",
        "major_font_latin": "Consolas",
        "minor_font_latin": "Segoe UI",
        "major_font_jpan": "MS ゴシック",
        "minor_font_jpan": "メイリオ",
        "theme_name": "Tech Dark",
        "color_scheme_name": "Tech",
    },
    "casual": {
        "bg_color": "FFF8F0",
        "dk1": "333333",    # ダークグレーテキスト
        "lt1": "FFF8F0",    # ウォームホワイト背景
        "dk2": "555555",
        "lt2": "FFF0E0",
        "accent1": "FF6B35",  # オレンジ
        "accent2": "F7C948",  # イエロー
        "accent3": "06D6A0",  # ミント
        "accent4": "118AB2",  # ティール
        "accent5": "EF476F",  # コーラル
        "accent6": "8338EC",  # パープル
        "hlink": "118AB2",
        "folHlink": "8338EC",
        "major_font_latin": "Fredoka",
        "minor_font_latin": "Nunito",
        "major_font_jpan": "M PLUS Rounded 1c",
        "minor_font_jpan": "M PLUS Rounded 1c",
        "theme_name": "Casual Warm",
        "color_scheme_name": "Casual",
    },
    "formal": {
        "bg_color": "FFFFFF",
        "dk1": "1B2D45",    # ダークネイビーテキスト
        "lt1": "FFFFFF",    # ホワイト背景
        "dk2": "34495E",
        "lt2": "ECF0F1",
        "accent1": "1B3A5C",  # ネイビー
        "accent2": "2C5F8A",  # ミディアムブルー
        "accent3": "34495E",  # チャコール
        "accent4": "7F8C8D",  # グレー
        "accent5": "2980B9",  # ブルー
        "accent6": "16A085",  # ティール
        "hlink": "2980B9",
        "folHlink": "7F8C8D",
        "major_font_latin": "Georgia",
        "minor_font_latin": "Calibri",
        "major_font_jpan": "游明朝",
        "minor_font_jpan": "游ゴシック",
        "theme_name": "Formal Corporate",
        "color_scheme_name": "Formal",
    },
}

# ベーステンプレートのデフォルトパス
_DEFAULT_BASE_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "skills" / "daida-ai" / "assets" / "templates" / "tech.pptx"
)


def _qn(tag: str) -> str:
    """'a:solidFill' → '{http://...}solidFill' に変換"""
    nsmap = {"a": _A_NS, "p": _P_NS}
    prefix, local = tag.split(":")
    return f"{{{nsmap[prefix]}}}{local}"


def build_template(
    name: str,
    output_path: Path,
    *,
    base_template: Path | None = None,
) -> None:
    """テンプレート名からデザイン済みPPTXを生成する。

    Args:
        name: "tech", "casual", "formal"
        output_path: 出力ファイルパス
        base_template: ベーステンプレートのパス（省略時はデフォルト）

    Raises:
        ValueError: 不正なテンプレート名
    """
    if name not in TEMPLATE_DESIGNS:
        raise ValueError(f"Unknown template: {name}")

    design = TEMPLATE_DESIGNS[name]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    src = base_template or _DEFAULT_BASE_TEMPLATE
    # ベーステンプレートをコピーしてから内部XMLを書き換え
    shutil.copy2(str(src), str(output_path))
    _apply_design(output_path, design)


def _apply_design(pptx_path: Path, design: dict[str, str]) -> None:
    """PPTXファイル内のテーマ・マスターXMLを書き換える。"""
    # zipは in-place 更新不可なので、全エントリをメモリに読み込み→書き戻し
    zip_entries: list[tuple[zipfile.ZipInfo, bytes]] = []
    with zipfile.ZipFile(str(pptx_path), "r") as zf:
        for info in zf.infolist():
            zip_entries.append((info, zf.read(info)))

    # テーマXMLとマスターXMLを書き換え
    updated: dict[str, bytes] = {}

    theme_data = next(d for zi, d in zip_entries if zi.filename == "ppt/theme/theme1.xml")
    theme_root = etree.fromstring(theme_data)
    _apply_color_scheme(theme_root, design)
    _apply_font_scheme(theme_root, design)
    _apply_theme_name(theme_root, design)
    updated["ppt/theme/theme1.xml"] = etree.tostring(
        theme_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    master_data = next(d for zi, d in zip_entries if zi.filename == "ppt/slideMasters/slideMaster1.xml")
    master_root = etree.fromstring(master_data)
    _apply_background(master_root, design)
    updated["ppt/slideMasters/slideMaster1.xml"] = etree.tostring(
        master_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    # 元のZipInfoを保持して書き戻し
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf_out:
        for info, data in zip_entries:
            if info.filename in updated:
                zf_out.writestr(info, updated[info.filename])
            else:
                zf_out.writestr(info, data)

    pptx_path.write_bytes(buf.getvalue())


def _apply_color_scheme(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマのカラースキームを書き換える。"""
    nsmap = {"a": _A_NS}
    clr_scheme = theme_root.find(".//a:clrScheme", nsmap)
    clr_scheme.set("name", design.get("color_scheme_name", "Custom"))

    slots = ["dk1", "lt1", "dk2", "lt2",
             "accent1", "accent2", "accent3", "accent4",
             "accent5", "accent6", "hlink", "folHlink"]

    for slot_name in slots:
        if slot_name not in design:
            continue
        slot = clr_scheme.find(f"a:{slot_name}", nsmap)
        if slot is None:
            continue
        # 既存の子要素を削除
        for child in list(slot):
            slot.remove(child)
        # srgbClr で固定色を設定
        srgb = etree.SubElement(slot, _qn("a:srgbClr"))
        srgb.set("val", design[slot_name])


def _apply_font_scheme(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマのフォントスキームを書き換える。"""
    nsmap = {"a": _A_NS}
    font_scheme = theme_root.find(".//a:fontScheme", nsmap)

    for font_type in ["majorFont", "minorFont"]:
        font_elem = font_scheme.find(f"a:{font_type}", nsmap)
        if font_elem is None:
            continue

        # Latin フォント
        key_prefix = "major" if font_type == "majorFont" else "minor"
        latin_key = f"{key_prefix}_font_latin"
        if latin_key in design:
            latin = font_elem.find("a:latin", nsmap)
            if latin is not None:
                latin.set("typeface", design[latin_key])

        # 日本語フォント
        jpan_key = f"{key_prefix}_font_jpan"
        if jpan_key in design:
            jpan = font_elem.find("a:font[@script='Jpan']", nsmap)
            if jpan is not None:
                jpan.set("typeface", design[jpan_key])


def _apply_theme_name(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマ名を設定する。"""
    if "theme_name" in design:
        theme_root.set("name", design["theme_name"])


def _apply_background(master_root: etree._Element, design: dict[str, str]) -> None:
    """スライドマスターの背景を solidFill に書き換える。"""
    nsmap = {"a": _A_NS, "p": _P_NS}
    cSld = master_root.find("p:cSld", nsmap)
    if cSld is None:
        return

    # 既存の <p:bg> を削除
    existing_bg = cSld.find("p:bg", nsmap)
    if existing_bg is not None:
        cSld.remove(existing_bg)

    # 新しい <p:bg> を cSld の先頭に挿入
    bg = etree.Element(_qn("p:bg"))
    bgPr = etree.SubElement(bg, _qn("p:bgPr"))
    solidFill = etree.SubElement(bgPr, _qn("a:solidFill"))
    srgbClr = etree.SubElement(solidFill, _qn("a:srgbClr"))
    srgbClr.set("val", design["bg_color"])
    etree.SubElement(bgPr, _qn("a:effectLst"))

    # cSld の最初の子として挿入（spTree より前）
    cSld.insert(0, bg)
