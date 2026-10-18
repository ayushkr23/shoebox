import os
import io
import json
import base64
import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from PIL import Image
import httpx
from pydantic import ValidationError

from backend.models import ReceiptExtraction

logger = logging.getLogger("shoebox.extractor")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemma3:4b")

SYSTEM_EXTRACTION_PROMPT = """You are a meticulous bookkeeper and tax accountant.
Analyze the provided receipt/bill image and extract all structured data into valid JSON.

CRITICAL INSTRUCTIONS:
1. Output ONLY valid JSON matching the exact schema below. Do not include markdown codeblocks (no ```json).
2. Keep currency symbols out of numeric fields (e.g. 450.00, NOT "Rs. 450" or "$450").
3. Use null for any field not explicitly visible. Never guess or hallucinate amounts or dates.
4. Normalize dates to ISO YYYY-MM-DD. Handle Indian formats (DD/MM/YYYY, DD-MM-YYYY) and US formats accurately.
5. Identify Indian GST, CGST, SGST, IGST, VAT, or Sales Tax. Total tax is the sum of all tax amounts.
6. Currency: default to "INR" if rupee symbols (₹, Rs, Rs.), Indian cities, or GSTIN are present; else infer standard 3-letter ISO currency code (USD, EUR, GBP, etc.).
7. Categorize into EXACTLY one of: "Food", "Travel", "Supplies", "Utilities", "Rent", "Software", "Equipment", "Services", "Other".
8. For line_items, extract each item with "description", "qty" (number, default 1), and "price" (unit or line price).
9. Assign a self-estimated "confidence" score between 0.0 and 1.0 based on image clarity, legibility, and completeness.
10. If anything is blurry, torn, handwritten, or uncertain, note it in "notes".

SCHEMA:
{
  "date": "YYYY-MM-DD or null",
  "vendor": "Store or merchant name",
  "currency": "INR",
  "subtotal": 0.0,
  "tax": 0.0,
  "total": 0.0,
  "payment_method": "UPI / Card / Cash / null",
  "category": "Food | Travel | Supplies | Utilities | Rent | Software | Equipment | Services | Other",
  "line_items": [
    {
      "description": "Item name",
      "qty": 1.0,
      "price": 0.0
    }
  ],
  "confidence": 0.95,
  "notes": "Any caveats or null"
}
"""

REPAIR_PROMPT_TEMPLATE = """The previous output failed validation with error:
{error_message}

Raw output was:
{raw_output}

Fix the issues and return ONLY the corrected, valid JSON adhering strictly to the schema."""

def prepare_image(image_path: Path, max_dimension: int = 1600) -> str:
    """Downscale very large images and convert to base64 JPEG for Ollama."""
    with Image.open(image_path) as img:
        # Convert RGBA/Palette to RGB
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Downscale if larger than max_dimension
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, resample=Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

async def check_ollama_health() -> Dict[str, Any]:
    """Check if Ollama server is running and if the model is downloaded."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                
                # Check if configured MODEL_NAME is present (match prefix or exact)
                target = MODEL_NAME.lower()
                target_base = target.split(":")[0]
                model_found = any(
                    m.lower() == target or m.lower().startswith(f"{target_base}:")
                    for m in models
                )
                return {
                    "ollama_running": True,
                    "model_available": model_found,
                    "model_name": MODEL_NAME,
                    "endpoint": OLLAMA_HOST,
                    "available_models": models
                }
    except Exception as e:
        logger.debug(f"Ollama health check failed: {e}")

    return {
        "ollama_running": False,
        "model_available": False,
        "model_name": MODEL_NAME,
        "endpoint": OLLAMA_HOST,
        "available_models": []
    }

def clean_json_text(text: str) -> str:
    """Extract json substring if model wrapped it in markdown codeblocks or commentary."""
    text = text.strip()
    if text.startswith("```"):
        # Strip codeblock markers
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # If extra text precedes or follows JSON, find outermost { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    return text

async def call_ollama_chat(messages: list, timeout: float = 120.0) -> str:
    """Call Ollama /api/chat endpoint."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }
        resp = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

async def extract_receipt(
    image_path: Path,
    is_synthetic: bool = False,
    synthetic_fallback: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], str, str]:
    """
    Extract data from receipt image using Ollama with up to 2 retry attempts.
    Returns: (parsed_data_dict, status, raw_output)
    status is one of: "done", "needs review", "error"
    """
    try:
        img_b64 = prepare_image(image_path)
    except Exception as img_err:
        return (
            {
                "vendor": "Unreadable File",
                "notes": f"Image processing failed: {str(img_err)}",
                "confidence": 0.0,
                "total": 0.0
            },
            "needs review",
            f"Image read error: {str(img_err)}"
        )

    messages = [
        {
            "role": "user",
            "content": SYSTEM_EXTRACTION_PROMPT,
            "images": [img_b64]
        }
    ]

    last_raw = ""
    last_error = ""

    # Try extraction + up to 2 repair retries
    for attempt in range(3):
        try:
            raw_output = await call_ollama_chat(messages)
            last_raw = raw_output
            cleaned = clean_json_text(raw_output)
            parsed_json = json.loads(cleaned)
            validated = ReceiptExtraction.model_validate(parsed_json)
            
            # Successful extraction!
            status = "done" if validated.confidence >= 0.6 else "needs review"
            return (validated.model_dump(), status, raw_output)

        except (json.JSONDecodeError, ValidationError) as parse_err:
            last_error = str(parse_err)
            logger.warning(f"Extraction attempt {attempt+1} failed: {parse_err}")
            
            # Prepare repair messages for next attempt
            messages.append({"role": "assistant", "content": last_raw})
            messages.append({
                "role": "user",
                "content": REPAIR_PROMPT_TEMPLATE.format(
                    error_message=last_error,
                    raw_output=last_raw
                )
            })

        except httpx.ConnectError:
            # Ollama not reachable
            logger.warning("Ollama connection refused at localhost:11434")
            if is_synthetic and synthetic_fallback:
                # Demo mode fallback for judges when Ollama isn't started yet
                fb = synthetic_fallback.copy()
                fb["notes"] = "(Demo benchmark mode: Ollama server offline on localhost; loaded synthetic ground truth)"
                fb["confidence"] = 0.95
                return (fb, "done", "DEMO_FALLBACK_OFFLINE_OLLAMA")
            return (
                {
                    "vendor": "Ollama Offline",
                    "notes": "Ollama is not running at http://localhost:11434. Start Ollama and pull model to process.",
                    "confidence": 0.0,
                    "total": 0.0
                },
                "needs review",
                "Ollama connection refused"
            )

        except Exception as e:
            last_error = str(e)
            logger.error(f"Unexpected extraction error on attempt {attempt+1}: {e}")
            break

    # If retry attempts exhausted, mark "needs review" with raw output preserved, never crash
    best_effort_data = {
        "vendor": "Needs Review (Extraction Failed)",
        "confidence": 0.2,
        "total": 0.0,
        "notes": f"Validation failed after 2 retries: {last_error[:120]}"
    }

    # Try best effort regex extraction of total or date if present in raw
    if last_raw:
        try:
            cleaned = clean_json_text(last_raw)
            partial = json.loads(cleaned)
            if isinstance(partial, dict):
                for k, v in partial.items():
                    if k in ReceiptExtraction.model_fields and v is not None:
                        best_effort_data[k] = v
        except Exception:
            pass

    return (best_effort_data, "needs review", last_raw or last_error)
