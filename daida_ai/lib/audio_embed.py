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

# OOXML名前空間
_nsmap = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
}

# p14:media拡張のURI
_P14_MEDIA_URI = "{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}"


def _make_1x1_png() -> bytes:
    """1x1透明PNGバイナリを生成する（音声シェイプのアイコンプレースホルダ用）。"""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    # IHDR: 1x1, 8-bit RGBA
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    # IDAT: 1 transparent pixel (filter byte 0 + RGBA 0,0,0,0)
    raw_data = b"\x00\x00\x00\x00\x00"
    idat_data = zlib.compress(raw_data)
    return signature + _chunk(b"IHDR", ihdr_data) + _chunk(b"IDAT", idat_data) + _chunk(b"IEND", b"")


# モジュールレベルでキャッシュ
_ICON_PNG = _make_1x1_png()


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

    # 5. スライドXMLに音声シェイプを追加
    _add_audio_shape(slide, r_id_audio, r_id_media, r_id_icon, r_id_hlink, slide_idx)


def _add_audio_shape(
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
    # スライド上の位置（右下、小さいアイコン）
    x = Emu(8229600)   # ~3.2 inches from left
    y = Emu(5943600)   # ~2.3 inches from top
    cx = Emu(304800)   # ~0.12 inches width
    cy = Emu(304800)   # ~0.12 inches height

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
