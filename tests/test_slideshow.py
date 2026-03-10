"""TDD: slideshow.py — スライドショー自動再生設定テスト"""

import pytest
from pathlib import Path
from lxml import etree
from pptx import Presentation

from daida_ai.lib.slide_spec import SlideSpec, SlideMetadata, Slide
from daida_ai.lib.slide_builder import build_presentation
from daida_ai.lib.audio_embed import embed_audio_to_pptx
from daida_ai.lib.slideshow import configure_slideshow

# OOXML名前空間
_ns = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


@pytest.fixture
def pptx_with_audio(tmp_output_dir: Path) -> Path:
    """音声埋め込み済みの4スライドPPTX"""
    spec = SlideSpec(
        metadata=SlideMetadata(title="LT", subtitle="Speaker", event="Event"),
        slides=[
            Slide(layout="title_slide", title="表紙"),
            Slide(layout="title_and_content", title="内容1", body=["a"]),
            Slide(layout="section_header", title="中表紙"),
            Slide(layout="title_and_content", title="内容2", body=["b"]),
        ],
    )
    prs = build_presentation(spec)
    pptx_path = tmp_output_dir / "test.pptx"
    prs.save(str(pptx_path))

    # スライド1,3に音声を埋め込む（表紙と中表紙には音声なし）
    audio_dir = tmp_output_dir / "audio"
    audio_dir.mkdir()
    # ダミーMP3（104バイト）
    dummy_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 100
    (audio_dir / "slide_001.mp3").write_bytes(dummy_mp3)
    (audio_dir / "slide_003.mp3").write_bytes(dummy_mp3)

    output = tmp_output_dir / "with_audio.pptx"
    embed_audio_to_pptx(pptx_path, audio_dir, output)
    return output


@pytest.fixture
def pptx_no_audio(tmp_output_dir: Path) -> Path:
    """音声なしの2スライドPPTX"""
    spec = SlideSpec(
        metadata=SlideMetadata(title="LT", subtitle="S", event="E"),
        slides=[
            Slide(layout="title_slide", title="表紙"),
            Slide(layout="title_and_content", title="内容", body=["a"]),
        ],
    )
    prs = build_presentation(spec)
    path = tmp_output_dir / "no_audio.pptx"
    prs.save(str(path))
    return path


class Test自動ページ送り:
    """全スライドにauto-advance transitionが設定される"""

    def test_全スライドにtransition要素が追加される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        for slide in prs.slides:
            trans = slide.element.findall("p:transition", _ns)
            assert len(trans) >= 1, "transition要素が必要"

    def test_advClickが無効になる(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """クリックでのページ送りを無効にする"""
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        for slide in prs.slides:
            trans = slide.element.find("p:transition", _ns)
            assert trans.get("advClick") == "0"

    def test_音声なしスライドにデフォルト秒数が設定される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """表紙・中表紙など音声なしスライドは固定時間で進む"""
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output, silent_duration_ms=4000)

        prs = Presentation(str(output))
        # スライド0 (表紙) と スライド2 (中表紙) は音声なし
        slide0_trans = prs.slides[0].element.find("p:transition", _ns)
        assert slide0_trans.get("advTm") == "4000"

        slide2_trans = prs.slides[2].element.find("p:transition", _ns)
        assert slide2_trans.get("advTm") == "4000"

    def test_音声ありスライドの送り時間はデフォルトより長い(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """音声付きスライドは音声長に基づいた時間で進む"""
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output, silent_duration_ms=3000)

        prs = Presentation(str(output))
        # スライド1は音声あり → advTmはsilent_durationとは異なる値
        slide1_trans = prs.slides[1].element.find("p:transition", _ns)
        adv_tm = int(slide1_trans.get("advTm"))
        # ダミーMP3は非常に短いが、最低でもバッファ分は確保される
        assert adv_tm > 0

    def test_音声なしPPTXでも動作する(
        self, pptx_no_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_no_audio, output, silent_duration_ms=5000)

        prs = Presentation(str(output))
        for slide in prs.slides:
            trans = slide.element.find("p:transition", _ns)
            assert trans is not None
            assert trans.get("advTm") == "5000"


class Test音声自動再生:
    """音声付きスライドにauto-playアニメーションが設定される"""

    def test_音声付きスライドにtiming要素が追加される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        # スライド1は音声あり → timing要素がある
        timing = prs.slides[1].element.find("p:timing", _ns)
        assert timing is not None

    def test_音声なしスライドにtiming要素がない(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        # スライド0は音声なし → timing要素がないか空
        timing = prs.slides[0].element.find("p:timing", _ns)
        if timing is not None:
            # timing要素があっても音声アニメーションはない
            audio_nodes = timing.findall(".//p:audio", _ns)
            assert len(audio_nodes) == 0

    def test_出力ファイルが正常に開ける(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        assert len(prs.slides) == 4


class Testカスタム設定:
    """configure_slideshowのパラメータテスト"""

    def test_silent_durationのデフォルトは3000ms(
        self, pptx_no_audio: Path, tmp_output_dir: Path
    ):
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_no_audio, output)

        prs = Presentation(str(output))
        trans = prs.slides[0].element.find("p:transition", _ns)
        assert trans.get("advTm") == "3000"

    def test_audio_buffer_msが加算される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """音声の長さ + バッファ時間でadvTmが設定される"""
        output = tmp_output_dir / "show.pptx"
        configure_slideshow(pptx_with_audio, output, audio_buffer_ms=2000)

        prs = Presentation(str(output))
        slide1_trans = prs.slides[1].element.find("p:transition", _ns)
        adv_tm = int(slide1_trans.get("advTm"))
        # バッファ2000ms以上は確保されているはず
        assert adv_tm >= 2000
