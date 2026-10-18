# Shoebox Launch Demo Video 🎬

A cinematic 95-second launch-style product video for **Shoebox**, designed in the dark-glass aesthetic of **Linear x Raycast x Apple**:
- **Resolution**: 1080p Full HD (1920x1080)
- **Frame Rate**: 30.0 fps
- **Format**: MP4 (H.264 video, AAC audio, faststart enabled)
- **Audio Engineering**: EBU R128 loudness normalized (`-16 LUFS`, true peak `-1.5 dB`), voiceover ducked under custom analog ambient synth pad.
- **Visuals**: Animated gradient mesh (`#0A0B10`, `#6366F1`, `#14B8A6`, `#EC4899`), floating glass device framing with 3D tilt, smooth custom cursor with click ripples, kinetic typography cards, and burned-in captions.

---

## ⚡ One-Command Build

To regenerate the entire video pipeline from scratch:

```bash
# Generate voice narration, sound effects, and master ducked audio
python video/audio_gen.py

# Record live app footage from http://localhost:8000
python video/record_scenes.py

# Render and composite all scenes into shoebox_demo.mp4
python video/render.py
```

---

## 📋 Storyboard & Scene Breakdown

| # | Scene | Timing | Visual Technique | VO Core Message |
|---|---|---|---|---|
| **1** | **The Hook** | `00:00 - 00:09` | 3D drifting paper receipts piling up with soft shadows on `#0A0B10` mesh | *"Every small business has a shoebox. Bills pile up, and typing receipts into a spreadsheet eats hours every week."* |
| **2** | **Problem Turn** | `00:09 - 00:19` | Red alert pulse, glowing cloud icon, padlock cracking, data flying away | *"Cloud tools promise to fix it, but they want your financial data on someone else's server, at someone else's price."* |
| **3** | **Reveal** | `00:19 - 00:31` | Shoebox logo slam with glow, tagline, Gemma vision open-weight badge | *"Meet Shoebox. Drop the receipts, keep the privacy. Powered by Gemma, an open-weight vision model."* |
| **4** | **Privacy Proof** | `00:31 - 00:43` | Real browser footage: smooth cursor clicks "100% local" badge, expands panel showing `$0.00` cloud cost and `localhost:11434` | *"100% local. Zero cloud calls, zero telemetry, and $0.00 cost per document."* |
| **5** | **Magic Extraction** | `00:43 - 00:55` | Real footage: 4 receipts dropped into dropzone, scanning light beam sweep, live streaming rows, numbers counting up | *"Drop in photos. Gemma extracts date, vendor, tax, total, and line items in seconds."* |
| **6** | **Trust & Review** | `00:55 - 01:05` | Real footage: amber warning chip zoom, spring drawer slides in, image click-to-zoom, field editing with green toast | *"When it isn't sure, it flags an amber warning instead of guessing. You stay in control."* |
| **7** | **Output & Export** | `01:05 - 01:13` | Real footage: Download CSV dropdown, Excel-ready UTF-8 BOM spreadsheet generated | *"One click. A clean, Excel-ready spreadsheet with all deductions categorized."* |
| **8** | **Real Numbers** | `01:13 - 01:23` | 4 kinetic glass stat cards with tabular counting numbers | *"Real benchmarks: 2.3s per receipt · 100% accuracy · $0.00 cloud cost · 6m saved."* |
| **9** | **Close** | `01:23 - 01:35` | Glowing end card, project name, open weights badge | *"Shoebox: paperwork that stays on your desk. Built with Gemma + Ollama."* |

---

## 📊 Honest Numbers Audit

Every single number in the narration, captions, and visual cards originates from verified benchmarks:

| Spoken / Displayed Value | Metric Description | Exact Source |
|---|---|---|
| **`2.3s`** | Average inference time per receipt on laptop hardware | Measured in [`eval/results.json`](file:///d:/College%20resources/dev%20project/shoebox%20to%20cashflow/eval/results.json) (`2.322s` average) |
| **`100%`** | Overall field extraction accuracy across benchmarks | [`eval/results.json`](file:///d:/College%20resources/dev%20project/shoebox%20to%20cashflow/eval/results.json) (`overall_field_accuracy_pct: 100.0%`) |
| **`$0.00`** | Cloud API expense per document | Real-time Privacy Proof panel (`Cloud API cost: $0.00`) |
| **`6m 00s`** | Manual data entry time saved | Real-time Privacy Proof panel (`4 receipts × 90s = 360s = 6 mins`) |
| **`100% local`** | Zero outbound network calls | Grep URL audit confirming only `localhost:8000` and `localhost:11434` exist |

---

## 📁 Artifacts Produced

- **`video/shoebox_demo.mp4`**: Master 1080p 30fps video file (H.264 + AAC, <100 MB).
- **`video/captions.srt`**: SubRip subtitle file with synchronized timestamps.
- **`video/narration.txt`**: Timestamped director transcript.
- **`video/audio/master_audio.wav`**: Master ducked audio with EBU R128 normalization.
- **`video/clips/`**: Individual scene clips rendered at 1080p.
