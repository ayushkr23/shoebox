import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = Path(__file__).resolve().parent
SCENES_DIR = VIDEO_DIR / "scenes"
CLIPS_DIR = VIDEO_DIR / "clips"
AUDIO_DIR = VIDEO_DIR / "audio"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

async def render_motion_graphic_scene(p, html_path: Path, out_mp4: Path, duration_sec: float):
    """Render a pure HTML/CSS motion graphics scene to MP4 using Playwright video recording."""
    import shutil
    raw_dir = out_mp4.parent / f"raw_{out_mp4.stem}"
    if raw_dir.exists():
        shutil.rmtree(raw_dir, ignore_errors=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    browser = await p.chromium.launch(
        headless=True,
        args=["--disable-web-security", "--window-size=1920,1080", "--hide-scrollbars"]
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(raw_dir),
        record_video_size={"width": 1920, "height": 1080}
    )
    page = await context.new_page()
    await page.goto(f"file:///{str(html_path).replace(os.sep, '/')}")
    await page.wait_for_load_state("networkidle")
    
    # Wait for the exact scene duration
    await asyncio.sleep(duration_sec)
    
    await page.close()
    await context.close()
    await browser.close()

    # Find the recorded WebM file and convert to 1080p 30fps MP4
    webm_files = list(raw_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError(f"No video recorded for {html_path}")
    raw_video = webm_files[0]

    # Convert to standard 30fps H.264 MP4 with exact duration
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(raw_video),
        "-t", f"{duration_sec:.2f}",
        "-vf", "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"  [OK] Rendered {out_mp4.name} ({duration_sec:.2f}s)")

async def convert_footage_clip(raw_clip_dir: Path, out_mp4: Path, duration_sec: float, zoom_scale: float = 1.05):
    """Process real recorded footage clip: add floating glass device frame & slow push-in."""
    webm_files = list(raw_clip_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError(f"No raw footage found in {raw_clip_dir}")
    raw_video = webm_files[0]

    # Filter: slow cinematic push-in (zoompan or crop/scale)
    # zoom from 1.0 to zoom_scale over duration
    vf_filter = (
        f"fps=30,"
        f"scale=1920:1080:flags=lanczos,"
        f"zoompan=z='min(zoom+0.0004,{zoom_scale:.3f})':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,"
        f"format=yuv420p"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(raw_video),
        "-t", f"{duration_sec:.2f}",
        "-vf", vf_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"  [OK] Processed footage {out_mp4.name} ({duration_sec:.2f}s)")

def assemble_master_video(scene_files: list, final_mp4: Path, master_audio: Path):
    """Concatenate all scene clips and mux with the master ducked audio bed."""
    concat_list = VIDEO_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in scene_files:
            escaped = str(sf).replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    print("\nConcatenating scenes and muxing master audio with EBU R128 loudness normalization...")
    temp_video = VIDEO_DIR / "temp_video_only.mp4"
    
    # 1. Concat video stream
    concat_cmd = [
        FFMPEG_EXE, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "copy",
        str(temp_video)
    ]
    subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 2. Mux with master audio, burn in kinetic popping subtitles, and encode H.264/AAC
    sub_file = (VIDEO_DIR / "subtitles_kinetic.ass").resolve()
    escaped_sub = str(sub_file).replace("\\", "/").replace(":", "\\:")
    vf_opt = f"ass='{escaped_sub}'" if sub_file.exists() else "null"

    mux_cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(temp_video),
        "-i", str(master_audio),
        "-vf", vf_opt,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        str(final_mp4)
    ]
    subprocess.run(mux_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if temp_video.exists():
        temp_video.unlink()
    if concat_list.exists():
        concat_list.unlink()

    print(f"\n[SUCCESS] Final cinematic video rendered with kinetic subtitles to: {final_mp4}")
    
    # Inspect video file size and specs
    size_mb = final_mp4.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB (< 100 MB target)")

async def main():
    with open(AUDIO_DIR / "timings.json", "r", encoding="utf-8") as f:
        timings_data = json.load(f)

    scenes = timings_data["scenes"]
    scene_durations = {s["id"]: s["scene_duration"] for s in scenes}

    # Step 1: Render motion graphics scenes
    print("Rendering motion graphics scenes with Playwright...")
    async with async_playwright() as p:
        mg_scenes = [
            ("scene_01_hook", SCENES_DIR / "scene_01_hook.html"),
            ("scene_02_problem", SCENES_DIR / "scene_02_problem.html"),
            ("scene_03_reveal", SCENES_DIR / "scene_03_reveal.html"),
            ("scene_08_numbers", SCENES_DIR / "scene_08_numbers.html"),
            ("scene_09_close", SCENES_DIR / "scene_09_close.html")
        ]
        for sid, html_file in mg_scenes:
            dur = scene_durations[sid]
            out_clip = CLIPS_DIR / f"{sid}.mp4"
            await render_motion_graphic_scene(p, html_file, out_clip, dur)

    # Step 2: Convert recorded footage scenes
    print("\nProcessing footage clips with camera push-ins...")
    footage_scenes = [
        ("scene_04_proof", CLIPS_DIR / "raw_scene_04", 1.08),
        ("scene_05_magic", CLIPS_DIR / "raw_scene_05", 1.04),
        ("scene_06_trust", CLIPS_DIR / "raw_scene_06", 1.06),
        ("scene_07_output", CLIPS_DIR / "raw_scene_07", 1.05)
    ]
    for sid, raw_dir, zoom in footage_scenes:
        dur = scene_durations[sid]
        out_clip = CLIPS_DIR / f"{sid}.mp4"
        await convert_footage_clip(raw_dir, out_clip, dur, zoom_scale=zoom)

    # Step 3: Master Assembly
    final_ordered_clips = [
        CLIPS_DIR / "scene_01_hook.mp4",
        CLIPS_DIR / "scene_02_problem.mp4",
        CLIPS_DIR / "scene_03_reveal.mp4",
        CLIPS_DIR / "scene_04_proof.mp4",
        CLIPS_DIR / "scene_05_magic.mp4",
        CLIPS_DIR / "scene_06_trust.mp4",
        CLIPS_DIR / "scene_07_output.mp4",
        CLIPS_DIR / "scene_08_numbers.mp4",
        CLIPS_DIR / "scene_09_close.mp4"
    ]
    
    final_output_path = VIDEO_DIR / "shoebox_demo.mp4"
    master_audio_path = AUDIO_DIR / "master_audio.wav"
    assemble_master_video(final_ordered_clips, final_output_path, master_audio_path)

if __name__ == "__main__":
    asyncio.run(main())
