# Shoebox 📦

> **Drop the receipts. Keep the privacy.**  
> Transform physical receipt & invoice photos into clean, categorized spreadsheets using 100% local open-weight vision models. No cloud APIs, no subscriptions, zero data leaving your machine.

---

## ⚡ 5-Line Quickstart

```bash
# 1. Clone repository & install dependencies
pip install -r requirements.txt

# 2. Pull local multimodal Gemma vision model (in Ollama)
ollama pull gemma3:4b

# 3. Start Shoebox (starts local server on port 8000)
./run.sh   # On Windows: run.bat or python -m uvicorn backend.main:app --port 8000
```
Open **`http://localhost:8000`** in any browser.

---

## 🏗️ Architecture

Shoebox is engineered as a **local-first, zero-telemetry** appliance designed for small business owners, freelancers, and privacy-conscious professionals.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          LOCAL MACHINE                                 │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │               Vanilla Web UI (Dark Glass Fintech)              │   │
│   │       (index.html · styles.css · app.js · 100% Offline)         │   │
│   └───────────────▲───────────────────────────────┬────────────────┘   │
│                   │ SSE Real-time Stream          │ Drag & Drop Upload │
│                   │ (status & progress)           │ (Multipart / Form) │
│   ┌───────────────┴───────────────────────────────▼────────────────┐   │
│   │                 FastAPI Backend (localhost:8000)               │   │
│   │                                                                │   │
│   │   • Sequential Processing Queue & Error Boundary               │   │
│   │   • Image Downscaling & Preprocessing (Pillow Lanczos)         │   │
│   │   • Pydantic v2 Schema Validation & 2-Stage Repair Prompts     │   │
│   │   • Arithmetic Sanity Check (Tax & Line Items vs Total)        │   │
│   │   • Excel-Compatible UTF-8 BOM CSV Exporter                    │   │
│   └───────────────▲───────────────────────────────┬────────────────┘   │
│                   │                               │                    │
│     Read/Write    │                               │ Base64 Image +     │
│                   ▼                               ▼ Strict JSON Prompt │
│         ┌───────────────────┐           ┌───────────────────┐          │
│         │ SQLite Database   │           │ Ollama Runtime    │          │
│         │ (shoebox.db)      │           │ (localhost:11434) │          │
│         │                   │           │ Model: gemma3:4b  │          │
│         └───────────────────┘           └───────────────────┘          │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Technical Pillars
1. **Zero External Requests**: No CDN links, no external web fonts, no cloud trackers, and no telemetry. All styling is native CSS, all icons are inline SVG, and typography uses system font stacks (`-apple-system`, `Segoe UI`, `SF Mono`).
2. **Sequential Background Queue**: Prevents GPU memory thrashing on local hardware by queuing uploads and processing images sequentially.
3. **Pydantic v2 Validation & Self-Healing Retries**: If vision model output is malformed or misses fields, a 2-stage repair loop sends targeted feedback back to Ollama to fix JSON syntax without crashing the batch.
4. **Local SQLite Persistence**: Session data, line items, and audit trails persist across page refreshes in `data/shoebox.db`.
5. **Excel-Proof CSV Export**: Writes an explicit UTF-8 Byte Order Mark (`\ufeff`) so international currencies, rupee symbols, and decimal columns open seamlessly in Microsoft Excel and Apple Numbers.

---

## 🔒 Why Open-Weight and Local?

Cloud receipt scanning APIs (Google Document AI, AWS Textract, OpenAI Vision) come with severe trade-offs for freelancers and small businesses:

| Metric | Cloud Document AI | Shoebox (Local Open-Weight AI) |
|---|---|---|
| **Privacy & Confidentiality** | Uploads bank statements, client names, and spending habits to remote servers | **100% private**: Nothing leaves your RAM/disk |
| **Per-Document Cost** | \$0.05 – \$0.20 per scan (accumulates rapidly) | **\$0.00 forever** (unlimited scans) |
| **Offline Reliability** | Requires active internet; fails on planes or remote sites | **Works completely offline** |
| **Model Portability** | Locked to proprietary vendor endpoints | **Swappable**: change `MODEL_NAME` anytime |
| **Data Retention Compliance** | Complex vendor DPAs and privacy policies | **Zero compliance exposure**: Local SQLite storage |

### Swapping & Fine-Tuning Models
Shoebox connects to Ollama via standardized `/api/chat` with `format: "json"`. You can swap to any multimodal model (e.g. `gemma3:12b`, `llama3.2-vision:11b`, or a custom LoRA fine-tune trained on your specific regional invoices) by setting the environment variable:

```bash
export MODEL_NAME="gemma3:12b"
./run.sh
```

---

## 📊 Evaluation Benchmark Harness

Shoebox includes an automated accuracy evaluation harness in `eval/evaluate.py`. It computes field-level exact match, fuzzy matching, tolerance accuracy, and latency metrics against ground truth benchmarks.

### Running the Benchmark
```bash
python eval/evaluate.py --images-dir data/samples --ground-truth eval/ground_truth.example.csv
```

### Evaluation Criteria:
- **`date`**: Exact ISO format match (`YYYY-MM-DD`).
- **`vendor`**: Case-insensitive fuzzy match (Levenshtein / `difflib.SequenceMatcher` $\ge 0.85$).
- **`total`**: Numeric tolerance within $\pm 0.01$.
- **`tax`**: Numeric tolerance within $\pm 0.01$.

Results are saved to `eval/results.json` with per-receipt latencies and field breakdown.

---

## 🧪 Bundled Synthetic Demo Receipts

Shoebox includes a built-in Pillow generator (`backend/samples.py`) that generates 3 synthetic receipts representing common real-world edge cases:
1. **`sample_clean_cafe.png`**: Modern café receipt with Indian CGST/SGST tax breakdown, UPI reference, and itemized lines.
2. **`sample_crumpled_tech.png`**: Hardware invoice with simulated crumple creases, noise gradient, and rotation tilt.
3. **`sample_handwritten_freelance.png`**: Freelancer travel duty voucher with handwritten styling, rubber stamp simulation, and toll surcharges.

Click **"Try with 3 Sample Receipts"** in the UI to immediately load and evaluate them.

---

## 🛠️ Design Decisions & Edge Case Handling

1. **Arithmetic Discrepancy Flag**: If the sum of line items differs from the grand total by $>2\%$, an amber **Math mismatch** warning chip is added to the row.
2. **Indian & Global Currencies**: Defaults to `INR` when `₹`, `Rs`, `GSTIN`, or Indian cities appear, while accurately parsing `USD`, `EUR`, and `GBP`.
3. **Corrupted File Graceful Degradation**: Deliberately corrupted or unreadable images never crash the sequential queue; they are labeled **Needs Review** with raw diagnostics captured.
4. **Health Check Setup Screen**: If Ollama is not running on load, a full-screen helper appears with the exact `ollama serve` and `ollama pull` commands, alongside an offline demo preview toggle.
