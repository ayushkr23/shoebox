import os
import sys
import wave
import json
import subprocess
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import imageio_ffmpeg

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

VIDEO_DIR = Path(__file__).resolve().parent
AUDIO_DIR = VIDEO_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

SCENES_SCRIPT = [
    {
        "id": "scene_01_hook",
        "name": "Hook",
        "text": "Every small business has a shoebox. Bills pile up, and typing receipts into a spreadsheet eats hours every week.",
        "caption": "Every small business has a shoebox. Bills pile up, and typing receipts eats hours."
    },
    {
        "id": "scene_02_problem",
        "name": "Problem Turn",
        "text": "Cloud tools promise to fix it, but they want your financial data on someone else's server, at someone else's price.",
        "caption": "Cloud tools promise to fix it, but they want your financial data on someone else's server, at someone else's price."
    },
    {
        "id": "scene_03_reveal",
        "name": "Reveal",
        "text": "Meet Shoebox. Drop the receipts, keep the privacy. It runs entirely on this laptop, powered by Gemma, an open-weight vision model.",
        "caption": "Meet Shoebox. Drop the receipts, keep the privacy. Powered by Gemma, 100% local."
    },
    {
        "id": "scene_04_proof",
        "name": "Privacy Proof",
        "text": "One hundred percent local. Nothing leaves this device. Zero cloud API calls, zero telemetry, and zero cost per document.",
        "caption": "100% local. Zero cloud calls, zero telemetry, and $0.00 cost per document."
    },
    {
        "id": "scene_05_magic",
        "name": "Magic Extraction",
        "text": "Drop in photos. The scanning beam sweeps, and Gemma reads the date, vendor, tax, total, and line items in seconds.",
        "caption": "Drop in photos. Gemma extracts date, vendor, tax, total, and line items in seconds."
    },
    {
        "id": "scene_06_trust",
        "name": "Trust & Review",
        "text": "When it isn't sure, it flags an amber warning instead of guessing. Click any row to inspect the image and verify line items.",
        "caption": "When it isn't sure, it flags an amber warning instead of guessing. You stay in control."
    },
    {
        "id": "scene_07_output",
        "name": "Output & Export",
        "text": "One click. A clean, Excel-ready spreadsheet with all deductions categorized and formatted.",
        "caption": "One click. A clean, Excel-ready spreadsheet with all deductions categorized."
    },
    {
        "id": "scene_08_numbers",
        "name": "Real Numbers",
        "text": "Real benchmarks: two point three seconds per receipt, one hundred percent accuracy on evaluation, and six minutes saved.",
        "caption": "Real benchmarks: 2.3s per receipt · 100% accuracy · $0.00 cloud cost · 6m saved."
    },
    {
        "id": "scene_09_close",
        "name": "Close",
        "text": "Because the model is open, you can swap it or fine-tune it with zero permission and zero pricing. Shoebox: paperwork that stays on your desk.",
        "caption": "Shoebox: paperwork that stays on your desk. Built with Gemma and Ollama."
    }
]

def synthesize_line_windows(text: str, out_wav: Path):
    """Use native Windows SAPI SpeechSynthesizer for instant, reliable speech generation."""
    ps_cmd = f"""
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.Rate = 0
    $s.SetOutputToWaveFile('{str(out_wav).replace("'", "''")}')
    $s.Speak('{text.replace("'", "''")}')
    $s.Dispose()
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)

def synthesize_speech() -> list:
    scene_timings = []
    print("Synthesizing narration speech for all 9 scenes...")
    for item in SCENES_SCRIPT:
        wav_path = AUDIO_DIR / f"{item['id']}.wav"
        if not wav_path.exists() or wav_path.stat().st_size < 1000:
            synthesize_line_windows(item["text"], wav_path)

        with wave.open(str(wav_path), "r") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        scene_timings.append({
            **item,
            "wav_path": str(wav_path),
            "duration": round(duration, 3),
            "scene_duration": round(duration + 1.2, 2)
        })
        print(f"  [OK] {item['name']}: {duration:.2f}s (scene: {duration+1.2:.2f}s)")

    return scene_timings

def generate_sound_effects(sample_rate=48000):
    t_click = np.linspace(0, 0.05, int(sample_rate * 0.05), False)
    click_wave = np.sin(2 * np.pi * 1200 * t_click) * np.exp(-t_click * 120)
    click_wave = (click_wave * 0.45 * 32767).astype(np.int16)
    wavfile.write(str(AUDIO_DIR / "click.wav"), sample_rate, click_wave)

    t_whoosh = np.linspace(0, 0.45, int(sample_rate * 0.45), False)
    noise = np.random.uniform(-1, 1, len(t_whoosh))
    env = np.sin(np.pi * t_whoosh / 0.45) ** 2
    freq_sweep = np.sin(2 * np.pi * (180 + 320 * t_whoosh) * t_whoosh)
    whoosh_wave = (0.7 * noise + 0.3 * freq_sweep) * env * 0.5
    whoosh_wave = (whoosh_wave * 32767).astype(np.int16)
    wavfile.write(str(AUDIO_DIR / "whoosh.wav"), sample_rate, whoosh_wave)

    t_chime = np.linspace(0, 0.8, int(sample_rate * 0.8), False)
    chime_wave = (
        0.5 * np.sin(2 * np.pi * 587.33 * t_chime) +
        0.3 * np.sin(2 * np.pi * 880.00 * t_chime) +
        0.2 * np.sin(2 * np.pi * 1174.66 * t_chime)
    ) * np.exp(-t_chime * 4.5)
    chime_wave = (chime_wave * 0.5 * 32767).astype(np.int16)
    wavfile.write(str(AUDIO_DIR / "chime.wav"), sample_rate, chime_wave)
    print("  [OK] Generated click, whoosh, and chime SFX (48kHz)")

def generate_ambient_pad(total_duration, sample_rate=48000):
    t = np.linspace(0, total_duration, int(sample_rate * total_duration), False)
    sub = 0.35 * np.sin(2 * np.pi * 65.41 * t)
    chord_g = 0.22 * np.sin(2 * np.pi * 98.00 * t + 0.3)
    chord_eb = 0.18 * np.sin(2 * np.pi * 155.56 * t + 0.7)
    chord_bb = 0.14 * np.sin(2 * np.pi * 233.08 * t + 1.1)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * (1.0 / 18.0) * t)
    shimmer = 0.08 * np.sin(2 * np.pi * 523.25 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t))
    pad = (sub + chord_g + chord_eb + chord_bb + shimmer) * lfo

    fade_in_len = int(sample_rate * 2.0)
    fade_out_len = int(sample_rate * 3.0)
    pad[:fade_in_len] *= np.linspace(0, 1, fade_in_len)
    pad[-fade_out_len:] *= np.linspace(1, 0, fade_out_len)

    # Output 48kHz stereo float
    pad_stereo = np.column_stack((pad, pad))
    return pad_stereo

def convert_wav_to_48k_stereo(in_wav: Path) -> np.ndarray:
    """Use FFmpeg to cleanly resample any WAV to 48kHz stereo 32-bit float array."""
    temp_48k = in_wav.parent / f"temp_{in_wav.name}"
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(in_wav),
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(temp_48k)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sr, data = wavfile.read(str(temp_48k))
    if temp_48k.exists():
        temp_48k.unlink()
    # Normalize to -1.0 to 1.0 float32
    return data.astype(np.float32) / 32768.0

def build_srt_and_master(scene_timings):
    srt_lines = []
    current_time = 0.0
    narration_txt = []

    for i, s in enumerate(scene_timings, 1):
        start_t = current_time + 0.4
        end_t = start_t + s["duration"]

        def fmt_time(sec):
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s_rem = sec % 60
            ms = int((s_rem - int(s_rem)) * 1000)
            return f"{h:02d}:{m:02d}:{int(s_rem):02d},{ms:03d}"

        srt_lines.append(f"{i}\n{fmt_time(start_t)} --> {fmt_time(end_t)}\n{s['caption']}\n")
        narration_txt.append(f"[{fmt_time(start_t)} - {s['name']}]\n{s['text']}\n")
        s["start_time"] = current_time + 0.4
        current_time += s["scene_duration"]

    total_duration = current_time

    with open(VIDEO_DIR / "captions.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    with open(VIDEO_DIR / "narration.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(narration_txt))

    sr = 48000
    total_samples = int(total_duration * sr) + sr

    # 1. Master Voice Track (full 100% volume, loud and crystal clear)
    master_voice = np.zeros((total_samples, 2), dtype=np.float32)
    for s in scene_timings:
        v_data = convert_wav_to_48k_stereo(Path(s["wav_path"]))
        start_sample = int(s["start_time"] * sr)
        end_sample = start_sample + len(v_data)
        if end_sample > total_samples:
            v_data = v_data[:total_samples - start_sample]
            end_sample = total_samples
        master_voice[start_sample:end_sample] += v_data

    # 2. Ambient Music Bed (gentle background, 8% volume)
    pad_stereo = generate_ambient_pad(total_duration, sample_rate=sr)
    if len(pad_stereo) < total_samples:
        pad_stereo = np.pad(pad_stereo, ((0, total_samples - len(pad_stereo)), (0, 0)))
    else:
        pad_stereo = pad_stereo[:total_samples]

    # 3. Sound Effects Track (whooshes at scene cuts)
    sfx_track = np.zeros((total_samples, 2), dtype=np.float32)
    whoosh_data = convert_wav_to_48k_stereo(AUDIO_DIR / "whoosh.wav")
    chime_data = convert_wav_to_48k_stereo(AUDIO_DIR / "chime.wav")
    
    # Place whooshes at transitions between scenes
    trans_time = 0.0
    for s in scene_timings[1:]:
        trans_time += s["scene_duration"]
        w_idx = int(trans_time * sr)
        if w_idx + len(whoosh_data) < total_samples:
            sfx_track[w_idx:w_idx + len(whoosh_data)] += whoosh_data * 0.4

    # Place chime at magic extraction (scene 5 done, ~52s)
    c_idx = int(52.0 * sr)
    if c_idx + len(chime_data) < total_samples:
        sfx_track[c_idx:c_idx + len(chime_data)] += chime_data * 0.35

    # 4. Master Composite: Voice is primary (0.95), Ambient is quiet bed (0.08)
    mixed = (master_voice * 0.95) + (pad_stereo * 0.08) + (sfx_track * 0.20)

    # 5. Peak normalize to -1.0 dB (0.891 of full scale)
    peak = np.max(np.abs(mixed))
    if peak > 0:
        target_peak = 0.891 # -1.0 dB
        mixed = mixed * (target_peak / peak)

    # Convert to 16-bit PCM
    mixed_16bit = np.clip(mixed * 32767.0, -32768, 32767).astype(np.int16)
    
    master_audio_path = AUDIO_DIR / "master_audio.wav"
    wavfile.write(str(master_audio_path), sr, mixed_16bit)

    print(f"  [OK] Master high-clarity voiceover mixed to {master_audio_path}")
    print(f"      Total Video Duration: {total_duration:.2f} seconds")
    print(f"      Voice Peak: {np.max(np.abs(master_voice)):.2f}, Final Audio Peak: {np.max(np.abs(mixed)):.2f}")
    return scene_timings, total_duration

if __name__ == "__main__":
    generate_sound_effects()
    timings = synthesize_speech()
    timings, total_dur = build_srt_and_master(timings)
    with open(AUDIO_DIR / "timings.json", "w", encoding="utf-8") as f:
        json.dump({"total_duration": total_dur, "scenes": timings}, f, indent=2)
    print("Audio processing complete!")
