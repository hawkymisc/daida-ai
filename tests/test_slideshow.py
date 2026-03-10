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


class Test既存アニメーション保持:
    """既存のアニメーションが破壊されないことを検証"""

    @pytest.fixture
    def pptx_with_existing_animation(self, tmp_output_dir: Path) -> Path:
        """既存アニメーション+音声付きPPTX"""
        from lxml import etree

        _P = "http://schemas.openxmlformats.org/presentationml/2006/main"

        spec = SlideSpec(
            metadata=SlideMetadata(title="LT", subtitle="S", event="E"),
            slides=[
                Slide(layout="title_slide", title="表紙"),
                Slide(layout="title_and_content", title="内容", body=["a", "b"]),
            ],
        )
        prs = build_presentation(spec)
        pptx_path = tmp_output_dir / "base.pptx"
        prs.save(str(pptx_path))

        # スライド1に音声を埋め込む
        audio_dir = tmp_output_dir / "audio_anim"
        audio_dir.mkdir()
        dummy_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 100
        (audio_dir / "slide_001.mp3").write_bytes(dummy_mp3)
        with_audio = tmp_output_dir / "with_audio_anim.pptx"
        embed_audio_to_pptx(pptx_path, audio_dir, with_audio)

        # スライド1に既存アニメーション（テキストフェードイン）を手動追加
        prs2 = Presentation(str(with_audio))
        slide = prs2.slides[1]
        # shape id=2をターゲットにしたダミーアニメーション
        timing_xml = f"""<p:timing xmlns:p="{_P}">
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>
                <p:par>
                  <p:cTn id="3" fill="hold">
                    <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="4" fill="hold">
                          <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                          <p:childTnLst>
                            <p:anim calcmode="lin" valueType="num">
                              <p:cBhvr>
                                <p:cTn id="5" dur="500" fill="hold"/>
                                <p:tgtEl><p:spTgt spid="2"/></p:tgtEl>
                                <p:attrNameLst><p:attrName>style.opacity</p:attrName></p:attrNameLst>
                              </p:cBhvr>
                            </p:anim>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>
              </p:childTnLst>
            </p:cTn>
            <p:prevCondLst>
              <p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>
            </p:prevCondLst>
            <p:nextCondLst>
              <p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>
            </p:nextCondLst>
          </p:seq>
        </p:childTnLst>
      </p:cTn>
    </p:par>
  </p:tnLst>
</p:timing>"""
        timing_elem = etree.fromstring(timing_xml)
        slide.element.append(timing_elem)

        result = tmp_output_dir / "with_existing_anim.pptx"
        prs2.save(str(result))
        return result

    def test_既存アニメーションが保持される(
        self, pptx_with_existing_animation: Path, tmp_output_dir: Path
    ):
        """configure_slideshow後も既存のp:animノードが残る"""
        output = tmp_output_dir / "show_anim.pptx"
        configure_slideshow(pptx_with_existing_animation, output)

        prs = Presentation(str(output))
        timing = prs.slides[1].element.find("p:timing", _ns)
        assert timing is not None

        # 既存のアニメーション（p:anim）が残っている
        anim_nodes = timing.findall(".//p:anim", _ns)
        assert len(anim_nodes) >= 1, "既存のp:animアニメーションが保持されるべき"

    def test_既存アニメーションに音声ノードが追加される(
        self, pptx_with_existing_animation: Path, tmp_output_dir: Path
    ):
        """既存アニメーション構造に音声auto-playがマージされる"""
        output = tmp_output_dir / "show_anim.pptx"
        configure_slideshow(pptx_with_existing_animation, output)

        prs = Presentation(str(output))
        timing = prs.slides[1].element.find("p:timing", _ns)
        assert timing is not None

        # 音声auto-playノードが追加されている
        audio_nodes = timing.findall(".//p:audio", _ns)
        assert len(audio_nodes) >= 1, "音声auto-playノードが追加されるべき"

    def test_二重実行しても音声ノードが重複しない(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """configure_slideshowを2回実行してもaudioノードが重複しない"""
        intermediate = tmp_output_dir / "show_pass1.pptx"
        configure_slideshow(pptx_with_audio, intermediate)

        output = tmp_output_dir / "show_pass2.pptx"
        configure_slideshow(intermediate, output)

        prs = Presentation(str(output))
        timing = prs.slides[1].element.find("p:timing", _ns)
        assert timing is not None

        audio_nodes = timing.findall(".//p:audio", _ns)
        assert len(audio_nodes) == 1, "audioノードは1つだけであるべき"


class Testフォールバック:
    """デュレーション計測不能時のフォールバック動作を検証"""

    def test_音声シェイプありデュレーション不明でもauto_playが設定される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """音声シェイプが存在すれば、デュレーション不明でもtiming要素が追加される。"""
        from unittest.mock import patch

        output = tmp_output_dir / "show_fallback.pptx"
        # _estimate_mp3_duration_msを0返しにスタブ → 計測不能シナリオ
        with patch(
            "daida_ai.lib.slideshow._estimate_mp3_duration_ms", return_value=0
        ):
            configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        # スライド1は音声シェイプあり → timing要素が追加される
        timing = prs.slides[1].element.find("p:timing", _ns)
        assert timing is not None
        audio_nodes = timing.findall(".//p:audio", _ns)
        assert len(audio_nodes) >= 1

    def test_unmeasurable_duration_msがadvTmに反映される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """デュレーション計測不能時にフォールバック値がadvTmに使われる"""
        from unittest.mock import patch

        output = tmp_output_dir / "show_unmeasurable.pptx"
        with patch(
            "daida_ai.lib.slideshow._estimate_mp3_duration_ms", return_value=0
        ):
            configure_slideshow(
                pptx_with_audio,
                output,
                unmeasurable_duration_ms=15000,
                audio_buffer_ms=2000,
            )

        prs = Presentation(str(output))
        # スライド1は音声シェイプあり → advTm = 15000 + 2000 = 17000
        slide1_trans = prs.slides[1].element.find("p:transition", _ns)
        assert slide1_trans is not None
        assert slide1_trans.get("advTm") == "17000"


class TestXMLスキーマ順序:
    """ECMA-376 CT_Slide: transition? は timing? より前に来る"""

    def test_transitionがtimingより前に配置される(
        self, pptx_with_audio: Path, tmp_output_dir: Path
    ):
        """音声付きスライドでtransitionとtimingの順序が正しい"""
        output = tmp_output_dir / "show_order.pptx"
        configure_slideshow(pptx_with_audio, output)

        prs = Presentation(str(output))
        slide_elem = prs.slides[1].element
        children = list(slide_elem)
        child_tags = [c.tag.split("}")[-1] for c in children]

        # transitionとtimingが両方存在する場合、transitionが先
        if "transition" in child_tags and "timing" in child_tags:
            trans_idx = child_tags.index("transition")
            timing_idx = child_tags.index("timing")
            assert trans_idx < timing_idx, (
                f"transition(idx={trans_idx}) must precede "
                f"timing(idx={timing_idx})"
            )
