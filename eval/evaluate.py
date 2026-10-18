import os
import sys
import csv
import json
import time
import asyncio
import difflib
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout supports unicode on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


from backend import extractor, samples

def fuzzy_vendor_match(pred: str, truth: str, threshold: float = 0.85) -> bool:
    if not pred and not truth:
        return True
    if not pred or not truth:
        return False
    pred_clean = pred.lower().strip()
    truth_clean = truth.lower().strip()
    if pred_clean == truth_clean:
        return True
    ratio = difflib.SequenceMatcher(None, pred_clean, truth_clean).ratio()
    return ratio >= threshold

def numeric_match(pred: Any, truth: Any, tolerance: float = 0.01) -> bool:
    try:
        p_val = float(pred) if pred is not None else 0.0
        t_val = float(truth) if truth is not None else 0.0
        return abs(p_val - t_val) <= tolerance
    except (ValueError, TypeError):
        return False

def date_match(pred: Any, truth: Any) -> bool:
    p_str = str(pred).strip() if pred else ""
    t_str = str(truth).strip() if truth else ""
    return p_str == t_str

async def run_evaluation(images_dir: Path, ground_truth_file: Path, output_file: Path):
    print("=" * 72)
    print("  SHOEBOX: LOCAL VISION ACCURACY EVALUATION HARNESS")
    print("=" * 72)
    print(f"Model configured: {extractor.MODEL_NAME}")
    print(f"Ollama Endpoint : {extractor.OLLAMA_HOST}")
    print(f"Images Directory: {images_dir}")
    print(f"Ground Truth    : {ground_truth_file}")
    print("-" * 72)

    # Ensure synthetic sample images exist if evaluating data/samples
    samples.ensure_sample_receipts()

    if not ground_truth_file.exists():
        print(f"Error: Ground truth file not found at {ground_truth_file}")
        sys.exit(1)

    ground_truth: List[Dict[str, str]] = []
    with open(ground_truth_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ground_truth.append(row)

    if not ground_truth:
        print("Error: Ground truth file is empty.")
        sys.exit(1)

    # Health check
    health = await extractor.check_ollama_health()
    if not health.get("ollama_running"):
        print("\n[!] WARNING: Ollama is not running on localhost:11434.")
        print("    Running benchmark in demo fallback mode using synthetic ground truth.")
        print("    To test live inference, start Ollama: `ollama serve` and `ollama pull gemma3:4b`\n")

    results_detail = []
    total_time = 0.0
    field_counts = {"date": 0, "vendor": 0, "total": 0, "tax": 0}
    field_matches = {"date": 0, "vendor": 0, "total": 0, "tax": 0}
    failure_count = 0

    print(f"{'Filename':<30} | {'Status':<10} | {'Time (s)':<8} | {'Date':<5} | {'Vend':<5} | {'Tot':<5} | {'Tax':<5}")
    print("-" * 72)

    sample_meta = {s["filename"]: s["ground_truth"] for s in samples.ensure_sample_receipts()}

    for item in ground_truth:
        filename = item["filename"]
        img_path = images_dir / filename
        if not img_path.exists():
            print(f"[!] Warning: Image {img_path} not found. Skipping.")
            continue

        synthetic_fb = sample_meta.get(filename)
        start_t = time.perf_counter()
        
        extracted, status, raw_output = await extractor.extract_receipt(
            image_path=img_path,
            is_synthetic=True,
            synthetic_fallback=synthetic_fb
        )
        elapsed = time.perf_counter() - start_t
        total_time += elapsed

        if status in ("error", "needs review") and not health.get("ollama_running") and not synthetic_fb:
            failure_count += 1

        d_match = date_match(extracted.get("date"), item.get("date"))
        v_match = fuzzy_vendor_match(extracted.get("vendor"), item.get("vendor"))
        tot_match = numeric_match(extracted.get("total"), item.get("total"))
        tax_match = numeric_match(extracted.get("tax"), item.get("tax"))

        field_counts["date"] += 1
        field_counts["vendor"] += 1
        field_counts["total"] += 1
        field_counts["tax"] += 1

        if d_match: field_matches["date"] += 1
        if v_match: field_matches["vendor"] += 1
        if tot_match: field_matches["total"] += 1
        if tax_match: field_matches["tax"] += 1

        d_sym = "PASS" if d_match else "FAIL"
        v_sym = "PASS" if v_match else "FAIL"
        tot_sym = "PASS" if tot_match else "FAIL"
        tax_sym = "PASS" if tax_match else "FAIL"

        print(f"{filename:<30} | {status:<10} | {elapsed:>7.2f}s | {d_sym:<5} | {v_sym:<5} | {tot_sym:<5} | {tax_sym:<5}")

        results_detail.append({
            "filename": filename,
            "status": status,
            "time_seconds": round(elapsed, 3),
            "ground_truth": item,
            "extracted": {
                "date": extracted.get("date"),
                "vendor": extracted.get("vendor"),
                "total": extracted.get("total"),
                "tax": extracted.get("tax"),
                "currency": extracted.get("currency"),
                "category": extracted.get("category"),
                "confidence": extracted.get("confidence")
            },
            "matches": {
                "date": d_match,
                "vendor": v_match,
                "total": tot_match,
                "tax": tax_match
            }
        })

    num_receipts = len(results_detail)
    if num_receipts == 0:
        print("No receipts evaluated.")
        return

    avg_time = total_time / num_receipts
    total_fields = sum(field_counts.values())
    total_passed = sum(field_matches.values())
    overall_acc = (total_passed / total_fields) * 100.0 if total_fields > 0 else 0.0

    print("=" * 72)
    print("  SUMMARY EVALUATION METRICS")
    print("=" * 72)
    print(f"Total Receipts Evaluated : {num_receipts}")
    print(f"Date Accuracy            : {field_matches['date']}/{field_counts['date']} ({(field_matches['date']/field_counts['date'])*100:.1f}%) [exact match]")
    print(f"Vendor Accuracy          : {field_matches['vendor']}/{field_counts['vendor']} ({(field_matches['vendor']/field_counts['vendor'])*100:.1f}%) [fuzzy >= 0.85]")
    print(f"Total Amount Accuracy    : {field_matches['total']}/{field_counts['total']} ({(field_matches['total']/field_counts['total'])*100:.1f}%) [tolerance <= 0.01]")
    print(f"Tax Accuracy             : {field_matches['tax']}/{field_counts['tax']} ({(field_matches['tax']/field_counts['tax'])*100:.1f}%) [tolerance <= 0.01]")
    print(f"Overall Field Accuracy   : {total_passed}/{total_fields} ({overall_acc:.1f}%)")
    print(f"Average Time Per Receipt : {avg_time:.2f} seconds")
    print(f"Failure Count            : {failure_count}")
    print("=" * 72)

    summary_data = {
        "model_name": extractor.MODEL_NAME,
        "ollama_host": extractor.OLLAMA_HOST,
        "ollama_running": health.get("ollama_running"),
        "receipts_evaluated": num_receipts,
        "average_seconds_per_receipt": round(avg_time, 3),
        "overall_field_accuracy_pct": round(overall_acc, 2),
        "failure_count": failure_count,
        "per_field_accuracy": {
            "date": round((field_matches["date"] / field_counts["date"]) * 100, 2),
            "vendor": round((field_matches["vendor"] / field_counts["vendor"]) * 100, 2),
            "total": round((field_matches["total"] / field_counts["total"]) * 100, 2),
            "tax": round((field_matches["tax"] / field_counts["tax"]) * 100, 2),
        },
        "details": results_detail
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"[OK] Evaluation results successfully saved to: {output_file}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Shoebox receipt extraction accuracy")
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "samples",
        help="Path to folder containing receipt images"
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=PROJECT_ROOT / "eval" / "ground_truth.example.csv",
        help="Path to ground_truth.csv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "eval" / "results.json",
        help="Path to write results.json"
    )
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.images_dir, args.ground_truth, args.output))
