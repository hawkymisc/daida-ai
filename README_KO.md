[English](./README.md) | [日本語](./README_JA.md) | [简体中文](./README_ZH.md) | [한국어](./README_KO.md)

# 대타AI

발표 자료를 자동 생성하는 Claude Code Plugin — AI가 대신 등판합니다.

> **daida-ai** (일본어 *daida* 代打 — 대타에서 유래): 마치 대타가 타석에 들어서듯, 이 플러그인이 여러분 대신 프레젠테이션 전체를 완성해 줍니다.

## 기능 개요

1. 발표 주제를 입력하면 Markdown 형식의 아웃라인을 생성
2. 아웃라인을 기반으로 슬라이드 자료 생성
   - PowerPoint 형식으로 생성
   - 사전 설계된 슬라이드 템플릿 사용 (다크 테크, 웜 캐주얼, 포멀 비즈니스)
   - 빈 슬라이드가 아닌 전문 레이아웃을 기반으로 생성
   - 제목과 본문은 개요 보기에서 접근 가능한 플레이스홀더에 설정
3. 슬라이드 노트에 토크 스크립트(대본) 작성
   - 다양한 말하기 스타일 지원: 캐주얼, 키노트, 포멀, 유머
4. 토크 스크립트로 내레이션 음성 합성
   - 발음 사전으로 일반적인 TTS 오독 자동 교정
   - TTS 스크립트를 내보내서 수동 편집 가능
5. 합성된 음성을 슬라이드에 삽입
6. 슬라이드쇼 자동 재생 설정

## 지원 형식

PPTX 및 ODP (Open Document Presentation)

## 설치

### 사전 요구 사항

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 설치 완료
- Python 3.11 이상

### Step 1: 마켓플레이스 추가

Claude Code에서 실행:

```
/plugin marketplace add hawkymisc/daida-ai
```

### Step 2: 플러그인 설치

```
/plugin install daida-ai@hawkymisc-daida-ai
```

### Step 3: 초기 설정

처음 사용 시 `/daida-ai:relief-pitcher-ai`를 실행하면 설정 스크립트 실행을 요청받습니다.
Claude의 안내에 따라 다음 명령을 승인하세요:

```bash
bash <plugin-dir>/skills/relief-pitcher-ai/scripts/setup.sh
```

Python 가상 환경 생성과 종속 패키지 설치가 진행됩니다.

## 사용법

Claude Code에서 호출:

```
/daida-ai:relief-pitcher-ai
```

또는 자연어로 요청할 수 있습니다:

- "LT 자료 만들어줘"
- "프레젠테이션 만들어줘"
- "대타로 발표 자료 만들어줘"

### 워크플로우

대화형으로 다음을 질문합니다:

1. **주제**: 무엇에 대해 발표하는지
2. **대상**: 누구를 위한 발표인지
3. **시간**: 몇 분인지 (기본값: 5분)
4. **템플릿**: `tech` / `casual` / `formal`
5. **TTS 엔진**: `edge` (기본값) / `voicevox`

전체 파이프라인이 자동 실행됩니다: 아웃라인 → 슬라이드 → 토크 스크립트 → 음성 합성 → 음성 삽입 → 슬라이드쇼 설정.

### 도움말

"도움말", "사용법", "어떻게 동작해?"라고 물으면 전체 파이프라인 다이어그램을 볼 수 있습니다.

### 단계별 재시작

중간에 PPTX나 TTS 스크립트를 수정한 경우 "Step 4부터 다시 시작"이라고 말하면 해당 단계부터 재개할 수 있습니다.

일반적인 예시:
- PPTX를 수동 편집한 후 → "Step 4부터 다시 시작"으로 음성 재생성
- 발음을 수정한 후 → "Step 4c부터 다시 시작"으로 음성 합성만 재실행
- 템플릿을 변경하고 싶을 때 → "Step 2부터 다시 시작"으로 슬라이드 재생성

### TTS 발음 수정

TTS가 잘못된 발음을 생성하는 경우 다음 방법으로 수정할 수 있습니다:

- **발음 사전**: `skills/relief-pitcher-ai/assets/pronunciation_dict.tsv`에 치환 규칙을 정의 (내보내기 시 자동 적용)
- **수동 수정**: TTS 스크립트를 내보낸 후 텍스트 에디터에서 직접 편집

## 템플릿

| 템플릿 | 스타일 | 폰트 |
|--------|--------|------|
| `tech` | 다크 테마, 시안 액센트 | Noto Sans CJK JP |
| `casual` | 웜톤, 둥근 디자인 | Noto Sans CJK JP |
| `formal` | 화이트 베이스, 비즈니스 지향 | Noto Serif CJK JP / Noto Sans CJK JP |

> **참고**: 템플릿은 현재 일본어 콘텐츠에 최적화되어 있습니다. 다른 언어 사용 시 시스템 폰트가 대체됩니다. 한국어 최적 표시를 위해 Noto Sans CJK KR 설치를 권장합니다.

## 음성 합성 엔진

| 엔진 | 설명 | 비고 |
|------|------|------|
| edge-tts | Microsoft Edge TTS. 설치 불필요. 다국어 지원. | 기본값 |
| VOICEVOX | 캐릭터 음성 (예: 즌다몬). 일본어 TTS 엔진. | [VOICEVOX Engine](https://voicevox.hiroshiba.jp/) 실행 필요 |

## 검증

슬라이드 사양 JSON (LLM이 생성)에 대해 다음 검증이 자동으로 수행됩니다:

- 슬라이드 수 (1–20장)
- 레이아웃과 필드 일관성 (예: `two_content`에는 `left`/`right` 필수)
- 텍스트 길이 제한 (제목 100자, 본문 항목 200자 등)
- 오디오 파일 형식 (MP3/WAV) 및 크기 (최대 50MB)
- 예상 발화 시간 확인

## 주의사항

### LibreOffice Impress에서의 재생

자동 페이지 넘김 (음성 재생 종료 후 자동으로 다음 슬라이드로 이동)은 **PowerPoint (Windows / macOS)에서만 동작**합니다.

**LibreOffice Impress에서는 자동 페이지 넘김이 동작하지 않습니다**. 이는 LibreOffice가 PPTX 내의 타이밍 설정 (`advTm`)을 올바르게 처리하지 않는 알려진 제한 사항입니다 ([Bug 101527](https://bugs.documentfoundation.org/show_bug.cgi?id=101527)).

LibreOffice Impress에서 재생할 경우:
- **수동**으로 슬라이드를 넘기세요 (클릭 또는 방향키)
- 또는 LibreOffice의 "슬라이드 전환" 패널에서 각 슬라이드의 자동 전환 시간을 수동으로 설정하세요

### 폰트에 대하여

템플릿은 일본어 텍스트에 [Noto CJK](https://github.com/googlefonts/noto-cjk) 폰트를 사용합니다.
Windows, macOS, Linux 모두에서 사용 가능하지만, 미설치 시 OS 기본 폰트가 사용됩니다.
한국어 최적 표시를 위해 Noto Sans CJK KR 사전 설치를 권장합니다.

## 라이선스

MIT

---

> 본 문서는 [README.md](./README.md)의 한국어 번역입니다. 내용에 차이가 있을 경우 영문 버전이 우선합니다.
