"""音声ファイルのPPTX埋め込み

python-pptxは音声の直接埋め込みAPIを持たないため、
OPCパッケージレベルでメディアパーツを追加し、
スライドXMLに音声シェイプ（p:pic + audioFile）を挿入する。

PowerPoint互換性のため、以下の構造が必要:
- RT.AUDIO リレーションシップ → a:audioFile r:link
- RT.MEDIA リレーションシップ → p14:media r:embed
- RT.IMAGE リレーションシップ → a:blip r:embed（アイコン画像）
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from lxml import etree
from pptx import Presentation
from pptx.opc.package import Part, PackURI, RT
from pptx.util import Emu

# アイコンサイズとマージン定数 (EMU)
_ICON_SIZE = Emu(304800)    # 32×32px (約0.33 inches)
_ICON_MARGIN = Emu(228600)  # 右端・下端からのマージン (0.25 inches)

# OOXML名前空間
_nsmap = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
}

# p14:media拡張のURI
_P14_MEDIA_URI = "{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}"


def _make_speaker_icon_png() -> bytes:
    """32x32のスピーカーアイコンPNGを生成する。

    macOS PowerPoint互換性のため、1x1透明PNGではなく
    視認可能なスピーカーアイコンを使用する。
    """

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    width, height = 32, 32
    # スピーカーアイコンを描画（簡易ビットマップ）
    # 背景: #38BDF8 (tech accent), 前景: #1E293B (dark)
    bg = (0x38, 0xBD, 0xF8, 200)
    fg = (0x1E, 0x29, 0x3B, 255)
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter byte
        for x in range(width):
            # スピーカー形状: 左側に台形、右側に音波ライン
            in_body = 10 <= x <= 16 and 10 <= y <= 22
            in_cone = 6 <= x <= 10 and 12 <= y <= 20
            in_wave1 = x == 20 and 10 <= y <= 22
            in_wave2 = x == 24 and 8 <= y <= 24
            if in_body or in_cone or in_wave1 or in_wave2:
                raw_data += bytes(fg)
            else:
                raw_data += bytes(bg)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat_data = zlib.compress(raw_data)
    return signature + _chunk(b"IHDR", ihdr_data) + _chunk(b"IDAT", idat_data) + _chunk(b"IEND", b"")


# モジュールレベルでキャッシュ
_ICON_PNG = _make_speaker_icon_png()


def embed_audio_to_pptx(
    input_path: Path,
    audio_dir: Path,
    output_path: Path,
) -> int:
    """音声ファイルをPPTXの各スライドに埋め込む。

    音声ファイルは slide_000.mp3, slide_001.mp3, ... の命名規則。
    対応するファイルが存在するスライドにのみ埋め込む。

    Args:
        input_path: 入力PPTXファイルパス
        audio_dir: 音声ファイルディレクトリ
        output_path: 出力PPTXファイルパス

    Returns:
        埋め込まれた音声ファイル数
    """
    prs = Presentation(str(input_path))
    count = 0

    for i, slide in enumerate(prs.slides):
        audio_path = audio_dir / f"slide_{i:03d}.mp3"
        if not audio_path.exists():
            continue

        _embed_audio_in_slide(prs, slide, audio_path, i)
        count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return count


def _embed_audio_in_slide(prs, slide, audio_path: Path, slide_idx: int) -> None:
    """単一スライドに音声ファイルを埋め込む。

    PowerPoint互換のため3つのリレーションシップを作成:
    1. RT.AUDIO → a:audioFile r:link 用
    2. RT.MEDIA → p14:media r:embed 用
    3. RT.IMAGE → a:blip r:embed 用（アイコン画像）
    """
    audio_data = audio_path.read_bytes()
    part_name = f"/ppt/media/audio_slide{slide_idx:03d}.mp3"

    # 1. 音声パーツを作成
    audio_part = Part(
        PackURI(part_name),
        "audio/mpeg",
        prs.part.package,
        blob=audio_data,
    )

    # 2. リレーションシップを追加
    # RT.AUDIO: a:audioFile r:link が参照する
    r_id_audio = slide.part.relate_to(audio_part, RT.AUDIO)
    # RT.MEDIA: p14:media r:embed が参照する
    r_id_media = slide.part.relate_to(audio_part, RT.MEDIA)

    # 3. アイコン画像パーツを作成
    icon_part_name = f"/ppt/media/audio_icon{slide_idx:03d}.png"
    icon_part = Part(
        PackURI(icon_part_name),
        "image/png",
        prs.part.package,
        blob=_ICON_PNG,
    )
    r_id_icon = slide.part.relate_to(icon_part, RT.IMAGE)

    # 4. hlinkClick用のハイパーリンクリレーションシップを追加
    #    ppaction://media は外部URIとして扱う
    r_id_hlink = slide.part.rels.get_or_add_ext_rel(
        RT.HYPERLINK, "ppaction://media"
    )

    # 5. スライドXMLに音声シェイプを追加（slide渡しで動的位置計算）
    _add_audio_shape(prs, slide, r_id_audio, r_id_media, r_id_icon, r_id_hlink, slide_idx)


def _add_audio_shape(
    prs,
    slide,
    r_id_audio: str,
    r_id_media: str,
    r_id_icon: str,
    r_id_hlink: str,
    slide_idx: int,
) -> None:
    """スライドXMLにp:pic要素（音声コントロール）を追加する。

    PowerPoint互換のOOXML構造:
    - p:cNvPr: a:hlinkClick (RT.HYPERLINK → ppaction://media)
    - p:nvPr: a:audioFile (RT.AUDIO) + p14:media拡張 (RT.MEDIA)
    - p:blipFill: a:blip (RT.IMAGE, アイコン画像)
    """
    # スライド寸法から右下位置を動的計算（4:3/16:9いずれにも対応）
    slide_w = int(prs.slide_width)
    slide_h = int(prs.slide_height)
    icon_sz = int(_ICON_SIZE)
    margin = int(_ICON_MARGIN)
    x = Emu(slide_w - icon_sz - margin)
    y = Emu(slide_h - icon_sz - margin)
    cx = _ICON_SIZE
    cy = _ICON_SIZE

    shape_id = 10000 + slide_idx

    pic_xml = (
        f'<p:pic xmlns:a="{_nsmap["a"]}" '
        f'xmlns:r="{_nsmap["r"]}" '
        f'xmlns:p="{_nsmap["p"]}" '
        f'xmlns:p14="{_nsmap["p14"]}">'
        f'  <p:nvPicPr>'
        f'    <p:cNvPr id="{shape_id}" name="Audio {slide_idx}">'
        f'      <a:hlinkClick r:id="{r_id_hlink}" action="ppaction://media"/>'
        f'    </p:cNvPr>'
        f'    <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
        f'    <p:nvPr>'
        f'      <a:audioFile r:link="{r_id_audio}"/>'
        f'      <p:extLst>'
        f'        <p:ext uri="{_P14_MEDIA_URI}">'
        f'          <p14:media r:embed="{r_id_media}"/>'
        f'        </p:ext>'
        f'      </p:extLst>'
        f'    </p:nvPr>'
        f'  </p:nvPicPr>'
        f'  <p:blipFill>'
        f'    <a:blip r:embed="{r_id_icon}"/>'
        f'    <a:stretch><a:fillRect/></a:stretch>'
        f'  </p:blipFill>'
        f'  <p:spPr>'
        f'    <a:xfrm>'
        f'      <a:off x="{x}" y="{y}"/>'
        f'      <a:ext cx="{cx}" cy="{cy}"/>'
        f'    </a:xfrm>'
        f'    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'  </p:spPr>'
        f'</p:pic>'
    )

    pic_element = etree.fromstring(pic_xml)
    slide_element = slide.element
    sp_tree = slide_element.find(
        ".//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree"
    )
    if sp_tree is None:
        sp_tree = slide_element.find(
            ".//{http://schemas.openxmlformats.org/presentationml/2006/main}cSld"
        )
        if sp_tree is not None:
            sp_tree = sp_tree.find(
                "{http://schemas.openxmlformats.org/presentationml/2006/main}spTree"
            )

    if sp_tree is not None:
        sp_tree.append(pic_element)
