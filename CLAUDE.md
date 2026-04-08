# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Two-stage pipeline for turning raw customer review recordings into platform-ready social clips:

1. **`clip_finder.py`** — transcribes a video with Whisper, scores moments with Claude, and cuts the top clips via FFmpeg into `clips/`
2. **`producer.py`** — takes clips from `clips/`, adds animated bumpers (via Remotion), lower thirds, background music, and renders LinkedIn (1920×1080) and Instagram (1080×1920) outputs into `produced/`

## Running the pipeline

**Step 1 — Find clips:**
```bash
python3 clip_finder.py path/to/recording.mp4
```

**Step 2 — Produce platform videos:**
```bash
python3 producer.py --clips-dir clips/ --overlays none
```

Key `producer.py` flags:
- `--speaker-name "Jane Smith" --speaker-title "Head of RevOps, Acme"` — adds animated lower third
- `--music path/to/track.wav` or `--generate-music` — background music (mutually exclusive)
- `--overlays none` — skip animated clip overlays; omit to use defaults

**Preview bumpers in Remotion Studio:**
```bash
cd remotion && npx remotion studio
```

**Clear bumper cache** (required after changing bumper props):
```bash
rm remotion/cache/IntroBumper_* remotion/cache/OutroBumper_*
```

## Per-clip configuration (sidecar JSON)

Each clip can have a `clips/<stem>.json` alongside the MP4:
```json
{
  "question": "What was AgencyHandy like to set up?",
  "logoFile": "agency-handy.png",
  "bgColor": "#000000",
  "textColor": "#FFFFFF",
  "outroText": "You grow the agency.\nWe keep it running.",
  "musicFile": "music/track.wav",
  "speakerName": "Jane Smith",
  "speakerTitle": "Head of RevOps"
}
```
All keys are optional — missing keys fall back to defaults. `logoFile` must exist in `remotion/public/`. `musicFile` is relative to the project root and overrides `--music`/`--generate-music`.

## Architecture

### Python layer (`producer.py`)
- `load_clip_config(clip_path)` — loads sidecar JSON, merges with defaults
- `make_bumper()` — renders intro/outro via Remotion (cached by props hash in `remotion/cache/`) or falls back to Pillow PNG → FFmpeg
- `add_lower_third()` — renders `LowerThird` as a transparent WebM via Remotion, overlays with FFmpeg
- `add_clip_overlays()` — renders `ClipOverlay` as transparent WebM, overlays with FFmpeg
- `produce_clip()` — orchestrates the full pipeline for one clip: lower third → overlays → music → bumpers → concat → format renders

Remotion renders are cached by an MD5 of `composition:width:height:props:codec`. Delete cache files to force re-render.

### Remotion layer (`remotion/src/`)
- **`BumperBase.tsx`** — shared intro/outro component. Sizing uses `Math.min(width, height)` as the reference dimension so text/logo scale identically on 16:9 and 9:16. The `isIntro` prop switches between typewriter-question mode (intro) and logo+text mode (outro).
- **`IntroBumper.tsx` / `OutroBumper.tsx`** — thin wrappers that pass `isIntro` to `BumperBase`
- **`LowerThird.tsx`** — transparent overlay; composited over the clip in FFmpeg
- **`ClipOverlay.tsx`** — dispatches `OverlayEvent[]` to overlay components (`Highlight`, `Callout`, `Rating`, `Reaction`); duration is calculated from the last event frame
- **`Root.tsx`** — registers all Remotion compositions with default props for Studio preview

### Dependencies
- Python: `anthropic`, `whisper`, `Pillow` (optional, for fallback PNG rendering)
- System: `ffmpeg`, `ffprobe`, Node.js with `remotion` installed in `remotion/node_modules/`
