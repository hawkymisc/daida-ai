---
name: relief-pitcher-ai
description: >
  A skill that auto-generates presentation materials for talks (from LTs to 30-min talks).
  From a theme, it creates an outline, generates PowerPoint/ODP slides,
  writes talk scripts (speaker notes), synthesizes speech, embeds audio,
  and exports MP4 video — all in one pipeline.
  Use cases: (1) Generate a full presentation from a talk theme,
  (2) Create slides from an existing outline,
  (3) Add talk scripts to slides,
  (4) Synthesize speech from scripts and embed into slides,
  (5) Export the presentation as a video.
  Triggers: LT, lightning talk, presentation, slides, talk script,
  relief pitcher, speech synthesis, lecture, video, MP4,
  代打, プレゼン作成, スライド作成, 登壇, ライトニングトーク,
  音声合成, 講演, 動画。
---

# Relief Pitcher AI — Auto-Generate Presentation Skill

## Overview

Executes the full pipeline from theme input to a finished presentation.
Up through Step 6 (slideshow configuration), the output is a **complete PPTX**.
Step 7 can additionally **export as an MP4 video**, but requires extra external tools (LibreOffice, ffmpeg).
Since many users do not need video, **after completing Step 6, confirm whether video is needed; if not, skip Step 7.**

## Help Display

When the user asks "help", "how to use", "show me the workflow", etc., display the following pipeline diagram:

```
╔══════════════════════════════════════════════════════════════╗
║               Relief Pitcher AI Pipeline                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Step 1    Theme → Outline (Markdown)                        ║
║     │                                                        ║
║  Step 1.5  Outline → Slide Spec (JSON)                       ║
║     │                                                        ║
║  Step 1.7  Image Generation (SVG / Gemini) ── Optional       ║
║     │                                                        ║
║  Step 2    Slide Spec → PPTX Generation                      ║
║     │         ↕ User can review & edit the PPTX              ║
║  Step 3    Talk Script Update ──────────── Optional           ║
║     │                                                        ║
║  Step 4    Dict → TTS Script → Speech Synthesis              ║
║     │         ↕ User can review & edit pronunciation         ║
║  Step 5    Audio Files → Embed into PPTX                     ║
║     │                                                        ║
║  Step 6    Slideshow Auto-Play Configuration                 ║
║     │                                                        ║
║     ▼                                                        ║
║  Done!     presentation_final.pptx                           ║
║     │                                                        ║
║  Step 7    MP4 Video Export ───────────── Optional            ║
║     │       (with automatic validation)                      ║
║     ▼                                                        ║
║  Video!    presentation.mp4                                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Templates: tech / casual / formal                           ║
║  TTS: edge (default) / voicevox / elevenlabs / openai        ║
║  Output: PPTX / ODP (conversion option) / MP4 (video option) ║
╚══════════════════════════════════════════════════════════════╝
```

**Additional notes** (display alongside the pipeline diagram when showing help):
- You can run all steps automatically, or resume from any step
- Steps marked with `↕` allow the user to manually edit and go back
- Step 1.7 (image generation) and Step 3 (script update) are optional
- Step 7 (video export) is also optional. It requires additional tools (LibreOffice, ffmpeg); skip if video is not needed

## Prerequisites

On first run, execute the setup:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh
```

`setup.sh` installs Python dependencies and then automatically checks availability of video generation tools (LibreOffice, ffmpeg, pdftoppm).
If any tools show `[--]` in the output, **and the user wants video output**, guide them through installation.
If video is confirmed unnecessary, the tool-not-found warnings can be ignored.

## Common Pattern for Script Execution

All Python scripts are run via the `run.sh` wrapper (automatic venv resolution):

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh <script_name.py> [args...]
```

## Workflow Selection (Step Resume Support)

Confirm with the user:
1. **Full run**: Auto-generate everything from a theme
2. **Step-specific**: Start from a specific step (using existing files)

Confirm the output directory with the user (default: `./output/`)

### Video Output Confirmation

At the start of the workflow, confirm whether **MP4 video is also needed**.
**If the AskUserQuestion tool is available, always use it to confirm.**

> After the PPTX is complete, you can also export it as an MP4 video (Step 7).
> Video export requires LibreOffice and ffmpeg to be installed.
> Would you like to create a video as well? (We can skip it if not needed.)

- **"Yes" / "Video too" / "MP4 too"** → Execute through Step 7. Check tool availability during `setup.sh`
- **"No" / "Not needed" / "PPTX only"** → Complete at Step 6. Skip the Step 7 prompt entirely
- **No answer / Ambiguous** → Confirm again at Step 6 completion (see Step 6 guidance section)

### Step Resume / Interruption

After the user edits intermediate files (PPTX, TTS scripts, etc.),
the workflow can be resumed from a specified step.

**When the user says "I want to redo from Step N":**

1. Check that the "Required Input" from the table below is available
2. If anything is missing, inform the user
3. If everything is ready, execute sequentially from that step to the end

| Resume Step | Required Input | Typical Use Case |
|---|---|---|
| Step 1 | Theme (verbal) | Start over from scratch |
| Step 1.5 | `output/outline.md` | Manually edited the outline |
| Step 1.7 | `output/slide_spec.json` | Manually edited the JSON spec |
| Step 2 | `output/slide_spec.json` | Manually edited the JSON spec |
| Step 3 | `output/presentation.pptx` | Manually edited the PPTX |
| Step 4 | `output/presentation.pptx` | Changed scripts / want to fix pronunciation |
| Step 5 | `output/presentation.pptx` + `output/audio/` | Replaced audio files |
| Step 6 | `output/presentation_with_audio.pptx` | Edited the audio-embedded PPTX |
| Step 7 | `output/presentation_final.pptx` + `output/audio/` | Want to regenerate the video |

**Common interruption patterns:**

- **"I edited the PPTX, recreate the audio"** → Resume from Step 4
- **"I fixed the pronunciation, just redo the audio"** → Resume from Step 4c (with `--script`)
- **"I want to change the slide content"** → Resume from Step 1.5 (edit JSON → Step 2 onward)
- **"I want to change the template"** → Change metadata.template in Step 1.5 → Resume from Step 2
- **"I want to change the TTS engine"** → Resume from Step 4 (change `--engine`)
- **"I just want to regenerate the video"** → Resume from Step 7

---

## Step 1: Outline Generation

### What you (Claude) should do

Gather the following from the user:
- **Theme**: What the talk is about
- **Audience**: Who the LT is for
- **Duration**: How many minutes (default: 5 min)
- **Event name**: Optional

Generate a Markdown outline with the following structure:

```markdown
# Presentation Title

## Introduction
- Point 1
- Point 2

## Main Topic 1: Section Name
- Point
- Point

## Main Topic 2: Section Name
- Point
- Point

## Summary
- Point
```

**Guidelines**:
- LT (5 min): 3-4 sections, 2-3 items each, 10 slides max
- Standard talk (15 min): 5-7 sections, 30 slides max
- Lecture (30 min): 7-10 sections, 60 slides max
- Target 30 sec to 1 min per slide

### Script Execution

Save the generated Markdown to a file, then pass it to the script:
```bash
# First save the outline Markdown to a file (using the Write tool)
# Then use the script to save to the designated path
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh generate_outline.py output/outline.md --stdin < output/outline_draft.md
```

---

## Step 1.5: Content Enrichment

### What you (Claude) should do

Read the outline generated in Step 1 and create a slide spec JSON following these guidelines:

**Enrichment guidelines**:
- **Add specific numbers and data** ("fast" → "10x faster")
- **Use `two_content` layout** when there are comparisons or contrasts
- **Follow the one-message-per-slide principle**
- **Limit bullet points to 3-5 items** (recommended; guardrails allow 1-8)
- For code examples, use `title_only` + code block in the note
- The first slide must be `title_slide`
- Use `section_header` for section dividers

**Confirm with the user**:
- Template: `tech` (default) / `casual` / `formal`
- Diagram density: `low` / `medium` (default) / `high`

### Diagram Density Levels

Adjust the proportion of slides with an `image` field according to the density level.

| Density | % of slides with image | Guideline |
|---|---|---|
| Low | ~20% (1-2 out of 10) | Key diagrams only. Primarily text and bullet points |
| Medium | ~40% (3-4 out of 10) | One diagram per section. Moderate use of flowcharts and comparison charts |
| High | ~60% (5-6 out of 10) | Visual elements on nearly every slide. Actively use architecture diagrams, charts, and illustrations |

**Default density by template** (determined in Step 1.5):

| Template | Default Density |
|---|---|
| `tech` | Medium |
| `casual` | Medium |
| `formal` | Low |

If the user explicitly specifies a density, use that. Otherwise, use the template default.

**Reference: Talk style and recommended density** (selected in Step 3):

| Talk Style | Recommended Density |
|---|---|
| `casual` | Medium |
| `keynote` | High |
| `formal` | Low |
| `humorous` | Medium |

> Talk style is selected in Step 3, so at the Step 1.5 stage, use the template default. Templates and talk styles that share a name (casual, formal) correspond to the same density.

### JSON Format

```json
{
  "metadata": {
    "title": "Presentation Title",
    "subtitle": "Speaker Name",
    "event": "Event Name",
    "template": "tech"
  },
  "slides": [
    {
      "layout": "title_slide",
      "title": "Presentation Title",
      "subtitle": "2026/03/10 @ Event Name - Speaker Name",
      "note": "Hello everyone. Today I'll be talking about X."
    },
    {
      "layout": "section_header",
      "title": "Section Name",
      "note": "Let's start by looking at X."
    },
    {
      "layout": "title_and_content",
      "title": "Slide Title",
      "body": ["Point 1", "Point 2", "Point 3"],
      "note": "Talk script (speaker notes)"
    },
    {
      "layout": "two_content",
      "title": "Comparison Title",
      "left": {"heading": "Left Heading", "body": ["Item 1", "Item 2"]},
      "right": {"heading": "Right Heading", "body": ["Item 1", "Item 2"]},
      "note": "Talk script"
    },
    {
      "layout": "title_only",
      "title": "Diagram / Code Slide",
      "note": "Explanation for this slide"
    },
    {
      "layout": "title_only",
      "title": "Architecture Diagram",
      "image": "images/architecture.png",
      "note": "This diagram shows the overall system architecture"
    },
    {
      "layout": "blank",
      "image": "images/fullscreen_photo.jpg",
      "note": "This photo shows the project results"
    }
  ]
}
```

**Available layouts**: `title_slide`, `section_header`, `title_and_content`, `two_content`, `title_only`, `blank`

**Image insertion**: Specify an image file path in the `image` field to insert an image into the slide.
- Paths are relative to the slide spec JSON file (e.g., if the spec is `output/slide_spec.json`, then `images/foo.png` resolves to `output/images/foo.png`)
- Images are automatically fitted within the content area while **maintaining aspect ratio**, centered both horizontally and vertically
- Images are placed behind text placeholders
- Available on all layouts. Recommended: `title_only` (title + diagram), `blank` (fullscreen diagram)
- Supported formats: PNG, JPEG, GIF, BMP, TIFF, **SVG** (auto-converted to PNG; requires cairosvg)

**Important**: **All slides** must include a talk script (speaker notes) in the `note` field (including `title_slide` and `section_header`). Slides without notes will have no audio generated and will advance quickly (3 seconds) during the slideshow. Notes can be updated in Step 3, but generate a first draft here.

### Script Execution

Save the generated JSON to a file, then pass it to the script (piping via echo may fail for large JSON):
```bash
# First save the slide spec JSON to a file (using the Write tool)
# Then run the script for validation & saving (specify duration with --duration)
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh enrich_outline.py output/slide_spec.json --stdin --duration 5 < output/slide_spec_draft.json
```

For a 15-minute talk:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh enrich_outline.py output/slide_spec.json --stdin --duration 15 < output/slide_spec_draft.json
```

`--duration` automatically adjusts the slide count limit and estimated speaking time limit.

---

## Step 1.7: Image Generation (Optional)

Generate images when you want to include diagrams or illustrations in slides.

### Choosing a Method

Follow this flowchart to decide the method:

```
1. Is GEMINI_API_KEY set?
   ├─ No → Generate everything as SVG (see "SVG Generation" section below)
   └─ Yes → Go to 2
2. What is the image content?
   ├─ SVG-suited (see list below) → Go to "SVG Generation" section
   └─ Nano Banana-suited (see list below) → Go to "Nano Banana" section
```

#### SVG-suited (Claude generates directly)

Use **SVG** for images matching the following. No API key needed, instant generation, editable.

- Flowcharts, process diagrams, step diagrams
- Architecture diagrams, system configuration diagrams
- Comparison charts (Before/After, A vs B)
- Bar charts, pie charts, simple charts
- Icons, logos, symbols
- Timelines, roadmaps
- Tables, matrix diagrams
- Text-heavy concept diagrams, mind maps

#### Nano Banana-suited (generated via Gemini API)

Use **Nano Banana** for images matching the following. Requires `GEMINI_API_KEY`.

- Photo-like backgrounds, landscapes, people
- Realistic texture illustrations, 3D rendering style
- Specific object depictions (product photo style, etc.)
- Hand-drawn, watercolor, oil painting style art
- Screenshot-style mockups

**When in doubt, use SVG**. SVG can be generated instantly and is easy to edit. Use Nano Banana only when you need "realism that SVG cannot express."

### Confirm with the user
- Which slides need images, and the content for each
- For Nano Banana: aspect ratio (`16:9` / `4:3` / `1:1`), resolution (`1K` / `2K` / `4K`)

---

### Nano Banana (Gemini Image Generation API)

**Prerequisites**: `GEMINI_API_KEY` environment variable

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh generate_image.py \
  --prompt "A professional conference stage with spotlight, modern tech event atmosphere" \
  --output output/images/slide1_background.png \
  --aspect-ratio 16:9 \
  --size 1K \
  --model pro
```

| Alias | Model ID | Use Case |
|---|---|---|
| `pro` | `gemini-3-pro-image-preview` | High quality, complex prompts, text rendering |
| `flash` | `gemini-3.1-flash-image-preview` | Fast generation, bulk generation |
| `legacy` | `gemini-2.5-flash-image` | Legacy model |

After generation, show the image to the user with the Read tool and adjust the prompt as needed.

---

### SVG Generation (No API Required)

You (Claude) generate SVG code directly.
**SVG files can be specified directly in the slide spec JSON `image` field** (automatically converted to PNG at build time).

**Prerequisites**: `cairosvg` must be installed (auto-installed if `setup.sh` has been run). If not installed:
```bash
pip install cairosvg
```

#### Procedure

1. Create the SVG file in `output/images/` using the **Write tool**
2. Specify the **SVG path** directly in the slide spec JSON `image` field
3. It will be automatically converted to PNG and inserted when `create_slides.py` runs in Step 2

Manual conversion is not needed. However, if you want to preview beforehand:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh svg_to_png.py input.svg output.png
```

#### SVG Sizes

| Use | viewBox | Description |
|---|---|---|
| Full slide | `0 0 1920 1080` | 16:9, suited for blank layout |
| Content area | `0 0 1200 900` | 4:3, suited for title_only layout |
| Icon / Logo | `0 0 400 400` | 1:1 |

#### SVG Font Size Requirements

SVG `font-size` is in px units within the viewBox coordinate system, but when embedded in PPTX, the image is scaled down, so the actual display size is determined by:

```
rendered_pt = f_svg × display_w_emu / (viewBox_w × 12700)
```

- `display_w_emu = min(max_w, max_h × viewBox_w / viewBox_h)`
- `max_w = slide_w − 2 × 457200` (left/right margins)
- `max_h = slide_h − img_top − 457200` (title_only: img_top=1600200, blank: img_top=457200)
- `12700` = EMU per 1pt (OOXML standard)

**Minimum standard for presentation materials: 12pt**. Follow these minimum SVG font-size values:

| viewBox | Layout | Min font-size | Recommended body | Recommended heading |
|---------|-----------|---------------|-----------|-------------|
| `1920×1080` | title_only | **35 px** | 40 px | 56 px |
| `1920×1080` | blank | **28 px** | 32 px | 48 px |
| `1200×900` | title_only | **29 px** | 32 px | 48 px |
| `1200×900` | blank | **24 px** | 28 px | 40 px |

> **Note**: Font sizes in SVGs are automatically validated when `create_slides.py` runs.
> A warning will be output if any text falls below the minimum.

#### Color Scheme by Template

| Template | Background | Accent 1 | Accent 2 | Text |
|---|---|---|---|---|
| tech | `#1E293B` | `#38BDF8` | `#818CF8` | `#E2E8F0` |
| casual | `#FFF8F0` | `#FF6B35` | `#06D6A0` | `#2D3748` |
| formal | `#FFFFFF` | `#1B2D45` | `#C49B66` | `#1B2D45` |

**Note**: Always specify `font-family="sans-serif"` for fonts. cairosvg automatically injects a Japanese font fallback, so Japanese text will not display as tofu (□). If `font-family` already contains `Hiragino` / `Yu Gothic` / `Noto Sans CJK JP`, injection is skipped.

#### SVG Pattern Examples

**Flowchart (3 steps)**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#818CF8"/>
    </marker>
  </defs>
  <!-- Step 1 -->
  <rect x="160" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="360" y="510" text-anchor="middle" fill="#1E293B"
        font-size="40" font-family="sans-serif" font-weight="bold">Step 1</text>
  <!-- Arrow 1→2 -->
  <line x1="560" y1="500" x2="720" y2="500" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Step 2 -->
  <rect x="760" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="960" y="510" text-anchor="middle" fill="#1E293B"
        font-size="40" font-family="sans-serif" font-weight="bold">Step 2</text>
  <!-- Arrow 2→3 -->
  <line x1="1160" y1="500" x2="1320" y2="500" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Step 3 -->
  <rect x="1360" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="1560" y="510" text-anchor="middle" fill="#1E293B"
        font-size="40" font-family="sans-serif" font-weight="bold">Step 3</text>
</svg>
```

**Comparison Chart (Before / After)**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <!-- Before -->
  <rect x="80" y="120" width="840" height="840" rx="20" fill="#334155" stroke="#475569" stroke-width="2"/>
  <text x="500" y="200" text-anchor="middle" fill="#EF4444"
        font-size="56" font-family="sans-serif" font-weight="bold">Before</text>
  <text x="500" y="400" text-anchor="middle" fill="#94A3B8"
        font-size="40" font-family="sans-serif">3 hours manual</text>
  <text x="500" y="460" text-anchor="middle" fill="#94A3B8"
        font-size="40" font-family="sans-serif">Error-prone</text>
  <text x="500" y="520" text-anchor="middle" fill="#94A3B8"
        font-size="40" font-family="sans-serif">Person-dependent</text>
  <!-- After -->
  <rect x="1000" y="120" width="840" height="840" rx="20" fill="#334155" stroke="#38BDF8" stroke-width="2"/>
  <text x="1420" y="200" text-anchor="middle" fill="#38BDF8"
        font-size="56" font-family="sans-serif" font-weight="bold">After</text>
  <text x="1420" y="400" text-anchor="middle" fill="#E2E8F0"
        font-size="40" font-family="sans-serif">5 min automated</text>
  <text x="1420" y="460" text-anchor="middle" fill="#E2E8F0"
        font-size="40" font-family="sans-serif">Consistent quality</text>
  <text x="1420" y="520" text-anchor="middle" fill="#E2E8F0"
        font-size="40" font-family="sans-serif">Anyone can run it</text>
</svg>
```

**Architecture Diagram (3 layers)**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#818CF8"/>
    </marker>
  </defs>
  <!-- Frontend -->
  <rect x="660" y="80" width="600" height="140" rx="16" fill="#38BDF8"/>
  <text x="960" y="160" text-anchor="middle" fill="#1E293B"
        font-size="40" font-family="sans-serif" font-weight="bold">Frontend</text>
  <!-- Arrow -->
  <line x1="960" y1="220" x2="960" y2="360" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- API -->
  <rect x="660" y="380" width="600" height="140" rx="16" fill="#818CF8"/>
  <text x="960" y="460" text-anchor="middle" fill="#FFFFFF"
        font-size="40" font-family="sans-serif" font-weight="bold">API Server</text>
  <!-- Arrow -->
  <line x1="960" y1="520" x2="960" y2="660" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Database -->
  <rect x="660" y="680" width="600" height="140" rx="16" fill="#334155" stroke="#38BDF8" stroke-width="2"/>
  <text x="960" y="760" text-anchor="middle" fill="#38BDF8"
        font-size="40" font-family="sans-serif" font-weight="bold">Database</text>
</svg>
```

---

### Workflow

1. In the Step 1.5 slide spec JSON, specify the output path in the `image` field
   - Nano Banana: specify a `.png` path
   - SVG: specify a `.svg` path (auto-converted)
2. Generate images in this step
3. Images are automatically inserted when slides are generated in Step 2

---

## Step 2: Slide Creation

### Script Execution

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh create_slides.py output/slide_spec.json output/presentation.pptx
```

To use a custom template:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh create_slides.py output/slide_spec.json output/presentation.pptx --template path/to/template.pptx
```

After generation, ask the user to review the PPTX.

---

## Step 3: Talk Script Update (Optional)

If notes are already included from Step 1.5, this step can be skipped.
Execute when the user wants to change the writing style or regenerate scripts.

### What you (Claude) should do

1. Read the current notes:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh write_talk_script.py output/presentation.pptx --read
```

2. Refer to `references/talk-styles.md` and regenerate scripts for all slides in the user's preferred style
   - Styles: `casual` (default) / `keynote` / `formal` / `humorous`

3. Save as a JSON array and write to the PPTX:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh write_talk_script.py output/presentation.pptx --notes-json output/notes.json --output output/presentation.pptx
```

---

## Step 4: Speech Synthesis

### Confirm with the user
- TTS engine: `edge` (default) / `voicevox` / `elevenlabs` / `openai`
- Voice:
  - edge: default `ja-JP-NanamiNeural`
  - voicevox: default `1` (Zundamon)
  - elevenlabs: pass a voice_id via `--voice` (user's Voice Clone IDs work too). Requires `ELEVENLABS_API_KEY` env var
  - openai: pass a preset voice name (e.g., `alloy`) via `--voice`. Requires `OPENAI_API_KEY` env var

### Step 4a: TTS Script Export

Export speaker notes as a text file for text-to-speech.
When a pronunciation dictionary (`--dict`) is specified, common mispronunciation patterns are automatically replaced.

With pronunciation dictionary (recommended):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh export_tts_script.py output/presentation.pptx output/tts_script.txt --dict ${CLAUDE_SKILL_DIR}/assets/pronunciation_dict.tsv
```

Without pronunciation dictionary:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh export_tts_script.py output/presentation.pptx output/tts_script.txt
```

### Step 4b: Review and Edit Pronunciation Text

Present the exported script file contents to the user.
Prompt them to check for items not auto-corrected by the dictionary, or project-specific terminology.

**Examples auto-corrected by dictionary:**
- "生成" → "せいせい", "Claude" → "クロード", "LLM" → "エルエルエム"

**Cases requiring manual correction:**
- Project-specific abbreviations and product names
- Technical terms not registered in the dictionary

If the user decides no corrections are needed, proceed to Step 4c (synthesize without `--script`, as before).
If entries should be added to the dictionary, update `pronunciation_dict.tsv`.

### Step 4c: Script Execution

With a corrected script file (`--script`):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine edge --script output/tts_script.txt
```

Without corrections (synthesize directly from PPTX notes, as before):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine edge
```

When using VOICEVOX (VOICEVOX Engine must be running beforehand):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine voicevox --script output/tts_script.txt
```

When using ElevenLabs (set `ELEVENLABS_API_KEY` beforehand; `--voice` accepts your Voice Clone's `voice_id`):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine elevenlabs --voice 21m00Tcm4TlvDq8ikWAM --script output/tts_script.txt
```

When using OpenAI TTS (set `OPENAI_API_KEY` beforehand; set `OPENAI_API_BASE` to use an OpenAI-compatible server):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine openai --voice alloy --script output/tts_script.txt
```

### TTS Failure Handling

If the TTS API fails for some or all slides, failed slides are skipped and audio files are generated only for successful ones (partial success).

- The script reports failure count to stderr and exits normally
- Slides without audio will auto-advance with default timing (3 seconds) in Step 6
- After TTS recovery, re-running Step 4c will generate audio for all slides
- The PPTX from Step 2 remains usable as-is (presentation is possible without audio)

---

## Step 5: Audio Embedding

### Script Execution

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh embed_audio.py output/presentation.pptx output/audio/ output/presentation_with_audio.pptx
```

---

## Step 6: Slideshow Auto-Play Configuration

Configures auto-advance and audio auto-play on the audio-embedded PPTX.
In PowerPoint (Windows / macOS), starting the slideshow plays it fully automatically to the end.
In LibreOffice Impress, auto-advance does not work, so slides must be advanced manually (see "Cross-Platform Compatibility Notes" for details).

- Slides with audio: auto-advance after audio playback + buffer (default 1 second)
- Slides without audio (title, section headers, etc.): auto-advance with fixed time (default 3 seconds)

### Script Execution

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_slideshow.py output/presentation_with_audio.pptx output/presentation_final.pptx
```

To adjust display timing:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_slideshow.py output/presentation_with_audio.pptx output/presentation_final.pptx --silent-duration 5000 --audio-buffer 2000
```

### User Guidance (Required)

After completing the slideshow configuration, **always communicate the following notes to the user**:

> **Pre-Slideshow Checklist**
>
> **For PowerPoint (Windows / macOS):**
> Verify that **"Use Timings"** is checked in the slideshow settings.
>
> - **Windows**: "Slide Show" tab → "Set Up Slide Show" → Check "Use Timings"
> - **macOS**: "Slide Show" menu → "Set Up Show..." → "Options" → Check "Use Timings"
>
> If this is unchecked, auto-advance and audio auto-play will not work.
>
> **For LibreOffice Impress:**
> Auto-advance does not work. Please **advance slides manually** during the slideshow (click or arrow keys). Audio will auto-play on each slide.

### Step 7 Guidance (Required)

Following the Step 6 guidance, **always confirm the following**:

> This presentation can also be exported as an MP4 video.
> This is useful for posting to YouTube or sharing in environments where PowerPoint is not available.
> However, additional tools (LibreOffice, ffmpeg) need to be installed.
> If you don't need video, the process is complete here. Would you like to create a video as well?

If the user responds with "Not needed", "No thanks", etc., **skip Step 7** and end the pipeline.

---

## Step 7: MP4 Video Export (Optional)

Generate an MP4 video from the PPTX and audio files.
Execute when you want to distribute or share the slideshow as a video.

### Confirm with the user

When the user responds "Create the video" to the Step 7 guidance, confirm the following:
- Video frame rate (default: 30fps)
- Display duration for slides without audio (default: 3 seconds)

### Prerequisites

Video generation requires additional tools. Availability is shown during `setup.sh` execution.

| Tool | Purpose | Required |
|--------|------|------|
| LibreOffice | PPTX → PDF → PNG rendering | Yes |
| ffmpeg | Video clip generation & concatenation | Yes |
| pdftoppm (poppler-utils) | PDF → PNG conversion (high quality) | Recommended (ffmpeg can substitute) |

If not installed:
```bash
# Ubuntu/Debian
sudo apt install libreoffice ffmpeg poppler-utils

# macOS
brew install libreoffice ffmpeg poppler
```

**Note on snap version of LibreOffice**: Use an output directory under `$HOME`.
Writing to `/tmp` etc. may fail due to sandbox restrictions.

### Script Execution

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_video.py output/presentation_final.pptx output/audio output/presentation.mp4
```

With options:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_video.py output/presentation_final.pptx output/audio output/presentation.mp4 --fps 30 --silent-duration 3.0
```

### Automatic Validation

After generation, the following checks are automatically performed:

| Check Item | Details |
|-------------|------|
| File existence | MP4 file exists and size > 0 |
| ffprobe read | File is not corrupted |
| Codecs | Video: H.264 / Audio: AAC |
| Resolution | Width and height are even numbers (libx264 compatible) |
| Duration | Positive value |

If validation fails, error details are displayed. Use `--skip-validation` to disable.

### User Guidance

After video generation is complete, communicate the following:

> **About the Video Output**
>
> - `presentation.mp4` has been generated
> - Display time for each slide is based on the actual audio file duration
> - Slides without audio display for 3 seconds by default
> - Playable with common video players (VLC, QuickTime, etc.)

---

## Format Conversion (Optional)

If ODP format is needed:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh convert_format.py output/presentation.pptx --outdir output/
```

**Prerequisite**: LibreOffice must be installed.

---

## Cross-Platform Compatibility Notes

### macOS PowerPoint Compatibility

PPTX files generated by Relief Pitcher AI work on **both macOS and Windows PowerPoint** as well as **LibreOffice Impress**.
Note the following technical constraints.

#### Audio Auto-Play (Step 6)

| Method | macOS | Windows | LibreOffice |
|------|-------|---------|-------------|
| `p:cmd type="call" cmd="playFrom(0)"` | Yes | Yes | Yes |
| `p:audio > p:cMediaNode` | No (treated as corrupt) | Yes | Yes |

- macOS PowerPoint treats `p:audio > p:cMediaNode` (OOXML media node method) as a **corrupted file**
- Instead, use `p:cmd type="call" cmd="playFrom(0)"` (command animation method)
- Specify `nodeType="afterEffect"` + `grpId="0"` for "auto-execute after previous animation"
- This method also works correctly on Windows PowerPoint / LibreOffice Impress

#### Audio Icon (Step 5)

| Icon | macOS | Windows |
|---------|-------|---------|
| 32x32 visible icon | Yes, displayed | Yes, displayed |
| 1x1 transparent PNG | No, invisible | Yes, auto-replaced with speaker icon |

- macOS PowerPoint displays transparent icons as-is (Windows auto-replaces with a speaker icon)
- Therefore, a **32x32 visible speaker icon** is used when embedding audio
- The icon is dynamically positioned at the **bottom-right corner** based on slide dimensions (0.25" margin from right and bottom edges)
- Correctly positioned at bottom-right for both 4:3 and 16:9 aspect ratios

#### Auto-Advance

| Method | macOS | Windows | LibreOffice |
|------|-------|---------|-------------|
| `p:transition advTm` | Yes | Yes | No (not supported) |

- **LibreOffice Impress does not support auto-advance**. Even with timing settings (`advTm`, `mainSeq.dur`) correctly configured in the PPTX, LibreOffice ignores them — this is a known limitation ([Bug 101527](https://bugs.documentfoundation.org/show_bug.cgi?id=101527))
- To play in LibreOffice, **advance slides manually** or manually set "auto-transition" time for each slide in LibreOffice's "Slide Transition" panel
- **Auto-advance works correctly in PowerPoint (Windows / macOS)**

---

## Reference

- `references/pptx-guide.md`: Details on layouts and placeholders
- `references/talk-styles.md`: Talk script style definitions
- `references/tts-plugins.md`: How to add TTS plugins
