# Video Automation

Two-stage pipeline for turning raw customer review recordings into platform-ready social clips.

## How it works

**Stage 1 — `clip_finder.py`**

Transcribes a video with Whisper, scores moments with Claude (looking for specific, comparative, or emotionally resonant quotes), and cuts the top 3 clips via FFmpeg into `clips/`.

**Stage 2 — `producer.py`**

Takes raw clips and layers on production elements — animated intro/outro bumpers (via Remotion), speaker lower thirds, and background music — then exports LinkedIn (1920×1080) and Instagram (1080×1920) versions into `produced/`.

## Requirements

**Python**
```bash
pip install anthropic openai-whisper Pillow
```

**System**
- `ffmpeg` and `ffprobe`
- Node.js with Remotion installed in `remotion/node_modules/`

```bash
cd remotion && npm install
```

**API key**
```bash
export ANTHROPIC_API_KEY=sk-...
```

## Usage

```bash
# Step 1 — find and cut clips
python3 clip_finder.py path/to/recording.mp4

# Step 2 — produce platform videos
python3 producer.py --clips-dir clips/ \
  --speaker-name "Jane Smith" \
  --speaker-title "Head of RevOps, Acme" \
  --music path/to/track.wav
```

Key `producer.py` flags:

| Flag | Description |
|---|---|
| `--speaker-name` / `--speaker-title` | Adds animated lower third |
| `--music <path>` | Background music track |
| `--generate-music` | Procedurally generate ambient music |
| `--overlays none` | Skip animated clip overlays |
| `--output-dir` | Output directory (default: `produced/`) |

## Per-clip configuration

Place a JSON sidecar next to any clip to override defaults:

```json
// clips/my-clip.json
{
  "question": "What was it like to get started?",
  "logoFile": "my-logo.png",
  "bgColor": "#000000",
  "textColor": "#FFFFFF",
  "outroText": "You grow the agency.\nWe keep it running.",
  "musicFile": "music/track.wav",
  "speakerName": "Jane Smith",
  "speakerTitle": "Head of RevOps"
}
```

All keys are optional. `logoFile` must exist in `remotion/public/`.

## Remotion

Bumpers and overlays are rendered as a React/TypeScript project in `remotion/`. Renders are cached by an MD5 of their props — delete cache files to force a re-render.

```bash
# Preview in Remotion Studio
cd remotion && npx remotion studio

# Clear bumper cache
rm remotion/cache/IntroBumper_* remotion/cache/OutroBumper_*
```
