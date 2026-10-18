import os
import sys
import json
import wave
import subprocess
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import imageio_ffmpeg

VIDEO_DIR = Path(__file__).resolve().parent
AUDIO_DIR = VIDEO_DIR / "audio"
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

MP3_NAME = "ElevenLabs_2026-10-18T21_31_08_Adam - American, Dark and Tough_pvc_sp100_s50_sb75_v4.mp3"
PROJECT_ROOT = VIDEO_DIR.parent
MP3_PATH = PROJECT_ROOT / MP3_NAME

def slice_elevenlabs_audio():
    print(f"Reading ElevenLabs audio from: {MP3_PATH}")
    if not MP3_PATH.exists():
        raise FileNotFoundError(f"Cannot find {MP3_PATH}")

    cuts = [
        ("scene_01_hook", 0.0, 7.78),
        ("scene_02_problem", 7.78, 15.26),
        ("scene_03_reveal", 15.26, 25.20),
        ("scene_04_proof", 25.20, 34.68),
        ("scene_05_magic", 34.68, 43.30),
        ("scene_06_trust", 43.30, 51.50),
        ("scene_07_output", 51.50, 57.23),
        ("scene_08_numbers", 57.23, 65.76),
        ("scene_09_close", 65.76, 75.65)
    ]

    for sid, st, en in cuts:
        out_wav = AUDIO_DIR / f"{sid}.wav"
        cmd = [
            FFMPEG_EXE, "-y",
            "-ss", f"{st:.3f}",
            "-to", f"{en:.3f}",
            "-i", str(MP3_PATH),
            "-ar", "48000",
            "-ac", "2",
            str(out_wav)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        dur = en - st
        print(f"  [OK] Extracted {sid}.wav ({dur:.2f}s)")

def convert_wav_to_48k_stereo(wav_path: Path, target_sr=48000) -> np.ndarray:
    sr, data = wavfile.read(str(wav_path))
    if data.ndim == 1:
        data = np.stack([data, data], axis=-1)
    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        data = data.astype(np.float32) / max_val
    elif np.issubdtype(data.dtype, np.floating):
        data = data.astype(np.float32)
    return data

def build_master_audio():
    with open(AUDIO_DIR / "timings.json", "r", encoding="utf-8") as f:
        timings_data = json.load(f)

    scenes = timings_data["scenes"]
    total_duration = timings_data["total_duration"]
    sr = 48000
    total_samples = int(total_duration * sr) + sr

    # 1. Master Voice Track with ElevenLabs Adam
    master_voice = np.zeros((total_samples, 2), dtype=np.float32)
    for s in scenes:
        wav_p = AUDIO_DIR / f"{s['id']}.wav"
        v_data = convert_wav_to_48k_stereo(wav_p)
        start_sample = int(s["start_time"] * sr)
        end_sample = start_sample + len(v_data)
        if end_sample > total_samples:
            v_data = v_data[:total_samples - start_sample]
            end_sample = total_samples
        master_voice[start_sample:end_sample] += v_data
        print(f"  Placed {s['id']} at {s['start_time']:.2f}s (len {len(v_data)/sr:.2f}s)")

    # 2. Ambient Music Bed
    pad_wav = AUDIO_DIR / "ambient_pad.wav"
    pad_stereo = convert_wav_to_48k_stereo(pad_wav)
    if len(pad_stereo) < total_samples:
        pad_stereo = np.pad(pad_stereo, ((0, total_samples - len(pad_stereo)), (0, 0)))
    else:
        pad_stereo = pad_stereo[:total_samples]

    # 3. Sound Effects Track
    sfx_track = np.zeros((total_samples, 2), dtype=np.float32)
    whoosh_data = convert_wav_to_48k_stereo(AUDIO_DIR / "whoosh.wav")
    chime_data = convert_wav_to_48k_stereo(AUDIO_DIR / "chime.wav")

    trans_time = 0.0
    for s in scenes[1:]:
        trans_time += s["scene_duration"]
        w_idx = int(trans_time * sr)
        if w_idx + len(whoosh_data) < total_samples:
            sfx_track[w_idx:w_idx + len(whoosh_data)] += whoosh_data * 0.4

    c_idx = int(52.0 * sr)
    if c_idx + len(chime_data) < total_samples:
        sfx_track[c_idx:c_idx + len(chime_data)] += chime_data * 0.35

    # 4. Master Composite: Voice is primary (0.95), Ambient is quiet bed (0.08)
    mixed = (master_voice * 0.95) + (pad_stereo * 0.08) + (sfx_track * 0.20)

    # 5. Peak normalize to -1.0 dB
    peak = np.max(np.abs(mixed))
    if peak > 0:
        target_peak = 0.891
        mixed = mixed * (target_peak / peak)

    mixed_16bit = np.clip(mixed * 32767.0, -32768, 32767).astype(np.int16)
    master_audio_path = AUDIO_DIR / "master_audio.wav"
    wavfile.write(str(master_audio_path), sr, mixed_16bit)
    print(f"[OK] Master audio with ElevenLabs voice written to: {master_audio_path}")

def remux_video():
    final_video = VIDEO_DIR / "shoebox_demo.mp4"
    master_audio = AUDIO_DIR / "master_audio.wav"
    temp_output = VIDEO_DIR / "shoebox_demo_elevenlabs.mp4"

    print("Remuxing video with new ElevenLabs master audio track...")
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(final_video),
        "-i", str(master_audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        str(temp_output)
    ]
    subprocess.run(cmd, check=True)

    if temp_output.exists() and temp_output.stat().st_size > 1000:
        os.replace(str(temp_output), str(final_video))
        print(f"[SUCCESS] Replaced {final_video} with ElevenLabs Adam voiceover!")

if __name__ == "__main__":
    slice_elevenlabs_audio()
    build_master_audio()
    remux_video()
