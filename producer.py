"""
producer.py — G2 Clip Production Layer

Takes raw MP4 clips from clip_finder.py and renders platform-ready versions:
  - LinkedIn (1920×1080, 16:9)
  - Instagram/TikTok (1080×1920, 9:16 blur-background)

Each output clip gets: intro bumper → lower third → background music → outro bumper.

Text rendering uses Pillow if available, otherwise falls back to boxes-only.
Install Pillow for text overlays: pip install Pillow

Usage:
  python3 producer.py \
    --clips-dir clips/ \
    --speaker-name "Jane Smith" \
    --speaker-title "Head of RevOps, Acme Corp" \
    --music path/to/track.mp3 \
    --output-dir produced/
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave as wave_mod
from pathlib import Path
from typing import Optional, Tuple

# Optional Pillow for text rendering
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ── Constants ─────────────────────────────────────────────────────────────────
BUMPER_DURATION = 2.5       # seconds for outro card
INTRO_BUMPER_DURATION = 4.6 # seconds for intro card (typewriter + reading hold)
BUMPER_FPS = 25
LOWER_THIRD_DURATION = 4.0  # how long speaker name shows
MUSIC_VOLUME = 0.12         # music level under speech (12%)
G2_RED_CSS = "#FF492C"
G2_RED_RGB = (255, 73, 44)
G2_DARK_CSS = "#1A1A2E"
G2_DARK_RGB = (26, 26, 46)

REMOTION_DIR = Path(__file__).parent / "remotion"
REMOTION_CACHE_DIR = REMOTION_DIR / "cache"


# ── Procedural music generation ───────────────────────────────────────────────

_SAMPLE_RATE = 44100
_CHORD_SECS  = 4.0
_CHORDS = [
    [220.00, 261.63, 329.63],  # Am
    [174.61, 220.00, 261.63],  # F
    [130.81, 164.81, 196.00],  # C
    [196.00, 246.94, 293.66],  # G
] * 2  # 4 chords × 4s × 2 repeats = 32s


def generate_music_wav(out_path, duration=32.0):
    """Write a 44100Hz 16-bit stereo WAV with an Am→F→C→G ambient chord loop."""
    attack  = int(0.080 * _SAMPLE_RATE)
    release = int(0.200 * _SAMPLE_RATE)
    amp_per_note = 0.06

    samples = []
    for chord_idx, notes in enumerate(_CHORDS):
        chord_len = int(_CHORD_SECS * _SAMPLE_RATE)
        for i in range(chord_len):
            t = i / _SAMPLE_RATE
            if i < attack:
                env = i / attack
            elif i > chord_len - release:
                env = (chord_len - i) / release
            else:
                env = 1.0
            val = sum(
                amp_per_note * env * (
                    math.sin(2 * math.pi * f * t) +
                    0.3 * math.sin(2 * math.pi * 2 * f * t)
                )
                for f in notes
            )
            samples.append(val)

    with wave_mod.open(str(out_path), 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        for s in samples:
            v = int(max(-32767, min(32767, s * 32767)))
            wf.writeframes(struct.pack('<hh', v, v))


# ── FFmpeg helpers ─────────────────────────────────────────────────────────────

def run_ffmpeg(args, label):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ffmpeg] ERROR in {label}:\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    return True


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def probe_video_size(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=s=x:p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        w, h = result.stdout.strip().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 1920, 1080


# ── Pillow-based image generation ────────────────────────────────────────────

def _try_load_font(size):
    """Try to load a system font at given size, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def make_bumper_png(out_png, width, height, line1="G2", line2="Customer Review"):
    """Render a G2-branded bumper frame as a PNG using Pillow."""
    img = Image.new("RGB", (width, height), G2_DARK_RGB)
    draw = ImageDraw.Draw(img)

    # G2 red border
    border = max(6, height // 80)
    draw.rectangle([0, 0, width - 1, height - 1], outline=G2_RED_RGB, width=border)

    # Horizontal accent bar (lower third of card)
    bar_y = height * 2 // 3
    draw.rectangle([border, bar_y, width - border, bar_y + border * 2],
                   fill=G2_RED_RGB)

    # "G2" large text
    font_big = _try_load_font(height // 6)
    font_small = _try_load_font(height // 14)

    # Centre "G2"
    bbox = draw.textbbox((0, 0), line1, font=font_big)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - tw) // 2, height // 4), line1, font=font_big, fill=(255, 255, 255))

    # Subtitle below
    bbox2 = draw.textbbox((0, 0), line2, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((width - tw2) // 2, height // 4 + th + height // 20),
              line2, font=font_small, fill=G2_RED_RGB)

    img.save(str(out_png))


def make_lower_third_png(out_png, width, height, speaker_name, speaker_title):
    """Render a transparent lower-third overlay PNG using Pillow."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bar_h = height // 7
    bar_y = height - bar_h - height // 20
    accent_h = max(4, height // 120)

    # Semi-transparent dark bar
    draw.rectangle([0, bar_y, width, bar_y + bar_h],
                   fill=(0, 0, 0, 165))
    # G2 red accent line
    draw.rectangle([0, bar_y - accent_h, width, bar_y],
                   fill=(*G2_RED_RGB, 255))

    font_name = _try_load_font(height // 22)
    font_title = _try_load_font(height // 32)

    name_y = bar_y + bar_h // 2 - height // 22 - 2
    title_y = bar_y + bar_h // 2 + 4

    draw.text((30, name_y), speaker_name, font=font_name, fill=(255, 255, 255, 255))
    draw.text((30, title_y), speaker_title, font=font_title, fill=(*G2_RED_RGB, 255))

    img.save(str(out_png))


# ── Remotion helpers ──────────────────────────────────────────────────────────

def _remotion_available() -> bool:
    return (REMOTION_DIR / "node_modules").exists()


def render_remotion(composition, out_path, width, height,
                    duration_secs, props=None, codec="h264"):
    """Render a Remotion composition to out_path via npx remotion render.

    Caches renders keyed by composition+size+props hash.
    Returns True on success, False on failure.
    """
    REMOTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Build cache key
    props_str = json.dumps(props, sort_keys=True) if props else "{}"
    key_src = f"{composition}:{width}:{height}:{props_str}:{codec}"
    cache_key = hashlib.md5(key_src.encode()).hexdigest()
    suffix = ".webm" if codec in ("vp8", "vp9") else ".mp4"
    cached = REMOTION_CACHE_DIR / f"{composition}_{cache_key}{suffix}"

    if cached.exists():
        shutil.copy2(cached, out_path)
        return True

    total_frames = int(duration_secs * BUMPER_FPS) - 1
    cmd = [
        "npx", "remotion", "render",
        composition,
        str(out_path),
        f"--width={width}",
        f"--height={height}",
        f"--frames=0-{total_frames}",
    ]
    if props:
        cmd.append(f"--props={props_str}")
    if codec in ("vp8", "vp9"):
        cmd += [f"--codec={codec}", "--crf=4"]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION_DIR))
    if result.returncode != 0:
        print(f"  [remotion] ERROR rendering {composition}:\n{result.stderr[-800:]}",
              file=sys.stderr)
        return False

    shutil.copy2(out_path, cached)
    return True


# ── Bumper generation ─────────────────────────────────────────────────────────

def load_clip_config(clip_path: Path) -> dict:
    """Load optional sidecar JSON for a clip. Returns a dict with all keys present."""
    defaults = {
        "question": None,
        "logoFile": None,
        "outroLogoFile": None,
        "bgColor": "#000000",
        "textColor": "#FFFFFF",
        "outroText": "You grow the agency.\nWe keep it running.",
        "musicFile": None,
        "speakerName": None,
        "speakerTitle": None,
    }
    json_path = clip_path.with_suffix(".json")
    if json_path.exists():
        with json_path.open() as f:
            data = json.load(f)
        defaults.update(data)
    return defaults


def make_bumper(out_path, width, height, line2="Customer Review", question=None, duration=None,
                bg_color=None, text_color=None, logo_file=None):
    if duration is None:
        duration = BUMPER_DURATION
    if _remotion_available():
        comp = "IntroBumper" if "Customer" in line2 else "OutroBumper"
        props = {"subtitle": line2}
        if question:
            props["question"] = question
        if bg_color:
            props["bgColor"] = bg_color
        if text_color:
            props["textColor"] = text_color
        if logo_file:
            props["logoFile"] = logo_file
        return render_remotion(comp, out_path, width, height, duration, props)
    silent = "anullsrc=r=44100:cl=stereo"
    if HAS_PILLOW:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            png_path = f.name
        try:
            make_bumper_png(png_path, width, height, "G2", line2)
            ok = run_ffmpeg(
                ["-loop", "1", "-i", png_path,
                 "-f", "lavfi", "-i", silent,
                 "-t", str(BUMPER_DURATION),
                 "-vf", f"scale={width}:{height}",
                 "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                 "-r", "25", "-shortest",
                 str(out_path)],
                "bumper"
            )
        finally:
            os.unlink(png_path)
        return ok
    else:
        # Fallback: drawbox-only branded card (no text)
        vf = (
            f"color=c={G2_DARK_CSS}:s={width}x{height}:d={BUMPER_DURATION},"
            f"drawbox=x=0:y=0:w=iw:h=ih:color={G2_RED_CSS}@1.0:t=8,"
            f"drawbox=x=iw/3:y=0:w=iw/3:h=ih:color={G2_RED_CSS}@0.15:t=fill"
        )
        return run_ffmpeg(
            ["-f", "lavfi", "-i", f"color=c={G2_DARK_CSS}:s={width}x{height}:d={BUMPER_DURATION}",
             "-f", "lavfi", "-i", silent,
             "-vf", vf,
             "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
             "-t", str(BUMPER_DURATION),
             str(out_path)],
            "bumper"
        )



# ── Lower third overlay ───────────────────────────────────────────────────────

def add_lower_third(in_path, out_path, speaker_name, speaker_title, width, height):
    if _remotion_available():
        lt_path = Path(str(out_path).replace(".mp4", "_lt.mp4"))
        ok = render_remotion(
            "LowerThird", lt_path, width, height,
            LOWER_THIRD_DURATION,
            {"name": speaker_name, "title": speaker_title},
        )
        if not ok:
            return False

        # Bar dimensions matching LowerThird.tsx
        bar_h = height // 7
        bar_bottom = height // 20
        bar_y = height - bar_h - bar_bottom

        # Render lower third on black background; blend=lighten composites it:
        # black pixels (bg) are transparent, white text always wins.
        ok = run_ffmpeg(
            ["-i", str(in_path), "-i", str(lt_path),
             "-filter_complex",
             f"[0:v]drawbox=x=0:y={bar_y}:w={width}:h={bar_h}"
             f":color=0x141414:t=fill:enable='lt(t,{LOWER_THIRD_DURATION})'[with_bar];"
             "[with_bar][1:v]blend=all_mode=lighten:eof_action=pass",
             "-map", "0:a?", "-c:v", "libx264", "-c:a", "aac",
             "-pix_fmt", "yuv420p", str(out_path)],
            "lower_third",
        )
        lt_path.unlink(missing_ok=True)
        return ok
    if HAS_PILLOW:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            png_path = f.name
        try:
            make_lower_third_png(png_path, width, height, speaker_name, speaker_title)
            # Overlay PNG for first LOWER_THIRD_DURATION seconds
            filter_complex = (
                f"[0:v][1:v]overlay=0:0:enable='lt(t,{LOWER_THIRD_DURATION})'"
            )
            ok = run_ffmpeg(
                ["-i", str(in_path),
                 "-loop", "1", "-i", png_path,
                 "-filter_complex", filter_complex,
                 "-map", "0:a?",
                 "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                 "-shortest",
                 str(out_path)],
                "lower_third"
            )
        finally:
            os.unlink(png_path)
        return ok
    else:
        # Fallback: colored bar only, no text
        bar_h = height // 7
        bar_y = height - bar_h - height // 20
        enable = f"lt(t,{LOWER_THIRD_DURATION})"
        vf = (
            f"drawbox=x=0:y={bar_y}:w=iw:h={bar_h}:color=black@0.65:t=fill:enable='{enable}',"
            f"drawbox=x=0:y={bar_y - 4}:w=iw:h=4:color={G2_RED_CSS}@1.0:t=fill:enable='{enable}'"
        )
        return run_ffmpeg(
            ["-i", str(in_path), "-vf", vf,
             "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
             str(out_path)],
            "lower_third"
        )


# ── Clip overlay (animated Remotion events) ───────────────────────────────────

DEFAULT_OVERLAY_EVENTS = [
    {"startFrame": 0, "durationFrames": 15, "type": "reaction"},
    {"startFrame": 30, "durationFrames": 75, "type": "rating",
     "stars": 5, "label": "G2 Review"},
]


def add_clip_overlays(in_path, out_path, width, height, overlay_events=None):
    """Composite animated ClipOverlay events over a clip via Remotion.

    overlay_events: list of OverlayEvent dicts. None → use DEFAULT_OVERLAY_EVENTS.
    Returns True on success (or skip), False on hard failure.
    """
    if not _remotion_available():
        return True  # skip silently; no Pillow fallback for complex overlays

    if overlay_events is None:
        overlay_events = DEFAULT_OVERLAY_EVENTS

    if not overlay_events:
        return True

    max_frame = max(e["startFrame"] + e["durationFrames"] for e in overlay_events)
    overlay_duration_secs = max_frame / BUMPER_FPS

    overlay_path = Path(str(out_path).replace(".mp4", "_ov.webm"))
    ok = render_remotion(
        "ClipOverlay", overlay_path, width, height,
        overlay_duration_secs,
        {"events": overlay_events},
        codec="vp8",
    )
    if not ok:
        return False

    ok = run_ffmpeg(
        ["-i", str(in_path), "-i", str(overlay_path),
         "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass",
         "-map", "0:a?", "-c:v", "libx264", "-c:a", "aac",
         "-pix_fmt", "yuv420p", str(out_path)],
        "clip_overlays",
    )
    overlay_path.unlink(missing_ok=True)
    return ok


# ── Music ducking ─────────────────────────────────────────────────────────────

def mix_music(in_path, out_path, music_path, duration):
    filter_a = (
        f"[1:a]volume={MUSIC_VOLUME},atrim=0:{duration},apad=whole_dur={duration}[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )
    return run_ffmpeg(
        ["-i", str(in_path),
         "-stream_loop", "-1", "-i", str(music_path),
         "-filter_complex", filter_a,
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac",
         "-t", str(duration),
         str(out_path)],
        "music_mix"
    )


# ── Concat ────────────────────────────────────────────────────────────────────

def concat_clips(parts, out_path):
    """Concatenate clips using the concat filter (handles mixed stream formats)."""
    inputs = []
    for p in parts:
        inputs += ["-i", str(p)]

    n = len(parts)
    # Build filter: scale all to common res first, then concat with audio
    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]setsar=1[v{i}];")
        filter_parts.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];")
    v_in = "".join(f"[v{i}][a{i}]" for i in range(n))
    filter_parts.append(f"{v_in}concat=n={n}:v=1:a=1[vout][aout]")

    return run_ffmpeg(
        inputs + [
            "-filter_complex", "".join(filter_parts),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
            str(out_path)
        ],
        "concat"
    )


# ── Format renders ────────────────────────────────────────────────────────────

def render_linkedin(in_path, out_path):
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    )
    return run_ffmpeg(
        ["-i", str(in_path),
         "-vf", vf,
         "-map", "0:v", "-map", "0:a",
         "-c:v", "libx264", "-c:a", "aac",
         "-crf", "23", "-preset", "fast",
         "-pix_fmt", "yuv420p",
         str(out_path)],
        "linkedin_render"
    )


def render_instagram(in_path, out_path):
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=20:20[bg];"
        "[0:v]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[vout]"
    )
    return run_ffmpeg(
        ["-i", str(in_path),
         "-filter_complex", filter_complex,
         "-map", "[vout]", "-map", "0:a",
         "-c:v", "libx264", "-c:a", "aac",
         "-crf", "23", "-preset", "fast",
         "-pix_fmt", "yuv420p",
         str(out_path)],
        "instagram_render"
    )


# ── Per-clip pipeline ─────────────────────────────────────────────────────────

def produce_clip(raw_clip, output_dir, speaker_name, speaker_title, music_path,
                 overlay_events=None):
    stem = raw_clip.stem
    print(f"\n[producer] Processing {raw_clip.name}")

    clip_cfg = load_clip_config(raw_clip)

    if clip_cfg["musicFile"]:
        clip_music = Path(clip_cfg["musicFile"])
        if not clip_music.exists():
            print(f"  [producer] WARNING: musicFile not found: {clip_music}, falling back to default music.", file=sys.stderr)
            clip_music = music_path
    else:
        clip_music = music_path

    width, height = probe_video_size(raw_clip)
    duration = probe_duration(raw_clip)
    if duration <= 0:
        print(f"  [producer] Could not determine duration, skipping.", file=sys.stderr)
        return None

    with tempfile.TemporaryDirectory(prefix="g2_producer_") as tmp:
        tmp = Path(tmp)

        main_clip = raw_clip

        # Step 1.5: Clip overlays (Remotion animated events)
        if _remotion_available() and overlay_events != []:
            overlay_out = tmp / "overlaid.mp4"
            print(f"  [producer] Adding clip overlays...")
            if not add_clip_overlays(main_clip, overlay_out, width, height, overlay_events):
                return None
            main_clip = overlay_out

        # Step 2: Music mix (optional)
        if clip_music:
            music_out = tmp / "with_music.mp4"
            print(f"  [producer] Mixing background music...")
            if not mix_music(main_clip, music_out, clip_music, duration):
                return None
            main_clip = music_out

        # Step 3a: LinkedIn — bumpers at 1920×1080, concat, render
        print(f"  [producer] Generating LinkedIn bumpers (1920×1080)...")
        li_intro = tmp / "intro_li.mp4"
        li_outro = tmp / "outro_li.mp4"
        if not make_bumper(li_intro, 1920, 1080, "Customer Review",
                           question=clip_cfg["question"], duration=INTRO_BUMPER_DURATION,
                           bg_color=clip_cfg["bgColor"], text_color=clip_cfg["textColor"],
                           logo_file=clip_cfg["logoFile"]):
            return None
        if not make_bumper(li_outro, 1920, 1080, clip_cfg["outroText"],
                           bg_color=clip_cfg["bgColor"], text_color=clip_cfg["textColor"],
                           logo_file=clip_cfg["outroLogoFile"] or clip_cfg["logoFile"]):
            return None

        li_clip = tmp / "li_clip.mp4"
        if not render_linkedin(main_clip, li_clip):
            return None

        # Lower third: LinkedIn only
        resolved_name = clip_cfg["speakerName"] or speaker_name
        resolved_title = clip_cfg["speakerTitle"] or speaker_title
        if resolved_name and resolved_title:
            li_lower = tmp / "li_lower.mp4"
            print(f"  [producer] Adding lower third (LinkedIn)...")
            if not add_lower_third(li_clip, li_lower, resolved_name, resolved_title, 1920, 1080):
                return None
            li_clip = li_lower

        li_concat = tmp / "concat_li.mp4"
        print(f"  [producer] Concatenating LinkedIn intro + clip + outro...")
        if not concat_clips([li_intro, li_clip, li_outro], li_concat):
            return None

        linkedin_out = output_dir / f"{stem}_linkedin.mp4"
        print(f"  [producer] Rendering LinkedIn (1920×1080)...")
        if not render_linkedin(li_concat, linkedin_out):
            return None

        # Step 3b: Instagram — bumpers at 1080×1920, concat, render
        print(f"  [producer] Generating Instagram bumpers (1080×1920)...")
        ig_intro = tmp / "intro_ig.mp4"
        ig_outro = tmp / "outro_ig.mp4"
        if not make_bumper(ig_intro, 1080, 1920, "Customer Review",
                           question=clip_cfg["question"], duration=INTRO_BUMPER_DURATION,
                           bg_color=clip_cfg["bgColor"], text_color=clip_cfg["textColor"],
                           logo_file=clip_cfg["logoFile"]):
            return None
        if not make_bumper(ig_outro, 1080, 1920, clip_cfg["outroText"],
                           bg_color=clip_cfg["bgColor"], text_color=clip_cfg["textColor"],
                           logo_file=clip_cfg["outroLogoFile"] or clip_cfg["logoFile"]):
            return None

        ig_clip = tmp / "ig_clip.mp4"
        if not render_instagram(main_clip, ig_clip):
            return None

        ig_concat = tmp / "concat_ig.mp4"
        print(f"  [producer] Concatenating Instagram intro + clip + outro...")
        if not concat_clips([ig_intro, ig_clip, ig_outro], ig_concat):
            return None

        instagram_out = output_dir / f"{stem}_instagram.mp4"
        print(f"  [producer] Rendering Instagram (1080×1920)...")
        if not render_instagram(ig_concat, instagram_out):
            return None

    print(f"  [producer] Done: {linkedin_out.name}, {instagram_out.name}")
    return linkedin_out, instagram_out


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="G2 Clip Producer — renders platform-ready clips from raw MP4s"
    )
    parser.add_argument("--clips-dir", default="clips")
    parser.add_argument("--speaker-name", default=None)
    parser.add_argument("--speaker-title", default=None)
    parser.add_argument("--music", default=None)
    parser.add_argument("--generate-music", action="store_true",
                        help="Generate a procedural ambient chord loop instead of using --music")
    parser.add_argument("--output-dir", default="produced")
    parser.add_argument(
        "--overlays", default=None,
        help="JSON array of overlay events (inline or path to .json file). "
             "Set to 'none' to disable overlays entirely."
    )
    args = parser.parse_args()

    # Parse --overlays
    overlay_events = None  # None → use defaults in add_clip_overlays
    if args.overlays:
        if args.overlays.lower() == "none":
            overlay_events = []  # empty list → skip overlays
        else:
            raw = args.overlays.strip()
            try:
                # Try as inline JSON first
                overlay_events = json.loads(raw)
            except json.JSONDecodeError:
                # Fall back to file path
                overlay_path = Path(raw)
                if not overlay_path.exists():
                    sys.exit(f"Error: --overlays file not found: {overlay_path}")
                with overlay_path.open() as f:
                    overlay_events = json.load(f)

    if args.music and args.generate_music:
        sys.exit("Error: --music and --generate-music are mutually exclusive; use one or the other.")

    clips_dir = Path(args.clips_dir)
    if not clips_dir.exists():
        sys.exit(f"Error: clips directory not found: {clips_dir}")

    raw_clips = sorted(clips_dir.glob("*.mp4"))
    if not raw_clips:
        sys.exit(f"Error: no MP4 files found in {clips_dir}")

    music_path = None
    _generated_music_tmp = None  # keep tempfile alive for the duration of main()
    if args.music:
        music_path = Path(args.music)
        if not music_path.exists():
            sys.exit(f"Error: music file not found: {music_path}")
    elif args.generate_music:
        _generated_music_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        _generated_music_tmp.close()
        print("[producer] Generating procedural background music (32s chord loop)...")
        generate_music_wav(_generated_music_tmp.name)
        music_path = Path(_generated_music_tmp.name)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if HAS_PILLOW:
        print("[producer] Text rendering: Pillow (full text overlays enabled)")
    else:
        print("[producer] Text rendering: unavailable (install Pillow for text: pip install Pillow)")

    print(f"[producer] Found {len(raw_clips)} clip(s) in {clips_dir}/")
    if args.speaker_name:
        print(f"[producer] Lower third: {args.speaker_name} — {args.speaker_title}")
    if args.generate_music:
        print(f"[producer] Background music: generated Am→F→C→G loop @ {int(MUSIC_VOLUME * 100)}%")
    elif music_path:
        print(f"[producer] Background music: {music_path.name} @ {int(MUSIC_VOLUME * 100)}%")

    if _remotion_available():
        print("[producer] Remotion: available (animated overlays enabled)")
    else:
        print("[producer] Remotion: node_modules not found — overlays skipped")

    produced = []
    try:
        for clip in raw_clips:
            result = produce_clip(
                clip, output_dir, args.speaker_name, args.speaker_title,
                music_path, overlay_events,
            )
            if result:
                produced.append(result)
    finally:
        if _generated_music_tmp:
            try:
                os.unlink(_generated_music_tmp.name)
            except OSError:
                pass

    total = len(produced)
    print(f"\n[producer] Done. {total}/{len(raw_clips)} clip(s) produced → {output_dir}/")
    for linkedin, instagram in produced:
        print(f"  {linkedin.name}")
        print(f"  {instagram.name}")


if __name__ == "__main__":
    main()
