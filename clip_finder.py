"""
clip_finder.py — G2 Review Clip Finder PoC

Pipeline: MP4 → Whisper transcription → Claude scoring → FFmpeg clips + summary
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic
import whisper

# ── Constants ────────────────────────────────────────────────────────────────
WHISPER_MODEL = "base"
PADDING_SECONDS = 1.5
MIN_CLIP_SECONDS = 10
MAX_CLIP_SECONDS = 45
TOP_N_CLIPS = 3
CLAUDE_MODEL = "claude-sonnet-4-6"

SCORING_PROMPT = """\
You are evaluating a customer review video transcript to find the top {top_n} most shareable moments.

A moment is shareable if it meets at least 2 of these 3 criteria:
- SPECIFIC: contains numbers, percentages, timeframes, or a concrete scenario
- COMPARATIVE: references before/after, a previous solution, or a competitor
- EMOTIONAL: conveys palpable feeling — relief, excitement, or frustration resolved

Here is the transcript with timestamps (each segment has start/end in seconds):

{transcript}

Return ONLY a JSON array with exactly {top_n} objects, ranked best-to-worst, each with:
{{
  "rank": <1-{top_n}>,
  "start": <float seconds>,
  "end": <float seconds>,
  "quote": "<exact or near-exact quote from transcript>",
  "criteria_met": ["SPECIFIC"|"COMPARATIVE"|"EMOTIONAL"],
  "rationale": "<one sentence explaining shareability>"
}}

Rules:
- Use the segment timestamps directly; do not invent times
- Prefer moments 10–45 seconds long when possible
- No overlapping moments
- Return only the JSON array, no other text
"""


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe(video_path: Path) -> list[dict]:
    """Transcribe video with Whisper, returning segments with start/end/text."""
    print(f"[whisper] Loading model '{WHISPER_MODEL}'...")
    model = whisper.load_model(WHISPER_MODEL)

    print(f"[whisper] Transcribing {video_path.name}...")
    result = model.transcribe(str(video_path), word_timestamps=True)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip()
        })

    print(f"[whisper] Got {len(segments)} segments")
    return segments


# ── Claude scoring ────────────────────────────────────────────────────────────

def score_moments(segments: list[dict], api_key: str) -> list[dict]:
    """Send transcript to Claude and get back top N shareable moments as JSON."""
    transcript_text = "\n".join(
        f"[{s['start']}s → {s['end']}s] {s['text']}"
        for s in segments
    )

    prompt = SCORING_PROMPT.format(
        top_n=TOP_N_CLIPS,
        transcript=transcript_text,
    )

    print(f"[claude] Scoring transcript ({len(segments)} segments)...")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    moments = json.loads(raw)
    print(f"[claude] Received {len(moments)} moments")
    return moments


# ── Clip extraction ───────────────────────────────────────────────────────────

def extract_clip(video_path: Path, start: float, end: float, out_path: Path) -> bool:
    """Use FFmpeg to cut a clip from video_path and save to out_path."""
    # Apply padding
    clip_start = max(0.0, start - PADDING_SECONDS)
    clip_end = end + PADDING_SECONDS
    duration = clip_end - clip_start

    # Enforce min/max
    if duration < MIN_CLIP_SECONDS:
        print(f"  [ffmpeg] Skipping clip — too short ({duration:.1f}s < {MIN_CLIP_SECONDS}s)")
        return False
    if duration > MAX_CLIP_SECONDS:
        clip_end = clip_start + MAX_CLIP_SECONDS
        duration = MAX_CLIP_SECONDS
        print(f"  [ffmpeg] Trimming clip to {MAX_CLIP_SECONDS}s")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(clip_start),
        "-i", str(video_path),
        "-t", str(duration),
        "-c", "copy",
        str(out_path),
    ]

    print(f"  [ffmpeg] {out_path.name} ({clip_start:.1f}s → {clip_start + duration:.1f}s)")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ffmpeg] ERROR: {result.stderr[-300:]}", file=sys.stderr)
        return False
    return True


# ── Summary ───────────────────────────────────────────────────────────────────

def write_summary(moments: list[dict], output_dir: Path, video_name: str) -> None:
    """Write a human-readable summary of the selected clips to summary.txt."""
    lines = [f"G2 Clip Finder — {video_name}", "=" * 60, ""]
    for m in moments:
        lines += [
            f"Clip #{m['rank']}",
            f"  Time:     {m['start']}s → {m['end']}s",
            f"  Criteria: {', '.join(m['criteria_met'])}",
            f"  Quote:    \"{m['quote']}\"",
            f"  Why:      {m['rationale']}",
            "",
        ]
    summary_path = output_dir / "summary.txt"
    summary_path.write_text("\n".join(lines))
    print(f"[summary] Written to {summary_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Find top shareable moments in a G2 review video")
    parser.add_argument("--video", required=True, help="Path to input MP4 file")
    parser.add_argument("--output-dir", default="clips", help="Output directory for clips (default: clips/)")
    parser.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY"),
                        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("Error: Anthropic API key required. Use --api-key or set ANTHROPIC_API_KEY.")

    video_path = Path(args.video)
    if not video_path.exists():
        sys.exit(f"Error: Video file not found: {video_path}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1 — Transcribe
    segments = transcribe(video_path)
    if not segments:
        sys.exit("Error: Whisper returned no segments.")

    # Step 2 — Score with Claude
    moments = score_moments(segments, args.api_key)

    # Step 3 — Extract clips
    produced = []
    for m in moments:
        out_path = output_dir / f"{video_path.stem}_clip_{m['rank']}.mp4"
        ok = extract_clip(video_path, float(m["start"]), float(m["end"]), out_path)
        if ok:
            produced.append((m, out_path))

    # Step 4 — Write summary
    write_summary(moments, output_dir, video_path.name)

    print(f"\nDone. {len(produced)}/{len(moments)} clips written to {output_dir}/")


if __name__ == "__main__":
    main()
