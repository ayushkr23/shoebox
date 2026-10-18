import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "shoebox.db"

def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receipts (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        image_path TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        date TEXT,
        vendor TEXT DEFAULT 'Unknown Vendor',
        currency TEXT DEFAULT 'INR',
        subtotal REAL,
        tax REAL,
        total REAL DEFAULT 0.0,
        payment_method TEXT,
        category TEXT DEFAULT 'Other',
        line_items TEXT DEFAULT '[]',
        confidence REAL DEFAULT 0.85,
        notes TEXT,
        raw_model_output TEXT,
        warnings TEXT DEFAULT '[]',
        is_synthetic INTEGER DEFAULT 0
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_created ON receipts(created_at DESC);")
    conn.commit()
    conn.close()

def compute_warnings(data: Dict[str, Any]) -> List[str]:
    """Calculate warning flags for low confidence, missing fields, or math mismatches."""
    warnings: List[str] = []
    
    # 1. Low confidence
    conf = data.get("confidence")
    if conf is not None:
        try:
            if float(conf) < 0.6:
                warnings.append(f"Low confidence ({float(conf):.0%})")
        except (ValueError, TypeError):
            pass

    # 2. Missing key fields
    missing = []
    if not data.get("date"):
        missing.append("date")
    if not data.get("vendor") or data.get("vendor") == "Unknown Vendor":
        missing.append("vendor")
    total_val = data.get("total")
    if total_val is None or total_val <= 0:
        missing.append("total")
    if missing:
        warnings.append(f"Missing fields: {', '.join(missing)}")

    # 3. Math mismatch check
    total = float(data.get("total") or 0.0)
    subtotal = data.get("subtotal")
    tax = data.get("tax")
    
    # Subtotal + tax vs Total check
    if subtotal is not None and tax is not None and total > 0:
        expected = float(subtotal) + float(tax)
        diff = abs(expected - total)
        if diff / total > 0.02 and diff > 0.5:
            warnings.append(f"Math mismatch: Subtotal ({subtotal:.2f}) + Tax ({tax:.2f}) = {expected:.2f} != Total ({total:.2f})")

    # Line items sum vs Total check
    raw_items = data.get("line_items", [])
    if isinstance(raw_items, str):
        try:
            raw_items = json.loads(raw_items)
        except Exception:
            raw_items = []
            
    if raw_items and total > 0:
        items_sum = sum(
            (float(it.get("qty", 1.0) or 1.0) * float(it.get("price", 0.0) or 0.0))
            for it in raw_items
            if isinstance(it, dict)
        )
        if items_sum > 0:
            # Could be items sum == total, OR items sum == subtotal (with tax added)
            diff_total = abs(items_sum - total)
            diff_subtotal = abs(items_sum - float(subtotal)) if subtotal is not None else 999.0
            
            # If it matches neither total nor subtotal within 2%:
            if (diff_total / total > 0.02 and diff_total > 0.5) and (diff_subtotal / total > 0.02 and diff_subtotal > 0.5):
                warnings.append(f"Math mismatch: Line items sum ({items_sum:.2f}) differs from Total ({total:.2f}) by >2%")

    return warnings

def serialize_row(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["line_items"] = json.loads(d["line_items"]) if d["line_items"] else []
    except Exception:
        d["line_items"] = []
    try:
        d["warnings"] = json.loads(d["warnings"]) if d["warnings"] else []
    except Exception:
        d["warnings"] = []
    d["is_synthetic"] = bool(d["is_synthetic"])
    return d

def create_receipt(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    warnings = compute_warnings(data)
    line_items_json = json.dumps(data.get("line_items", []))
    warnings_json = json.dumps(warnings)
    
    cursor.execute("""
    INSERT INTO receipts (
        id, filename, image_path, status, created_at, date, vendor,
        currency, subtotal, tax, total, payment_method, category,
        line_items, confidence, notes, raw_model_output, warnings, is_synthetic
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        data["filename"],
        data["image_path"],
        data.get("status", "queued"),
        data.get("created_at", datetime.now().isoformat()),
        data.get("date"),
        data.get("vendor", "Unknown Vendor"),
        data.get("currency", "INR"),
        data.get("subtotal"),
        data.get("tax"),
        data.get("total", 0.0),
        data.get("payment_method"),
        data.get("category", "Other"),
        line_items_json,
        data.get("confidence", 0.85),
        data.get("notes"),
        data.get("raw_model_output"),
        warnings_json,
        1 if data.get("is_synthetic") else 0
    ))
    conn.commit()
    conn.close()
    return get_receipt(data["id"])

def update_receipt(receipt_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    existing = get_receipt(receipt_id)
    if not existing:
        return None
    
    merged = {**existing, **updates}
    if "line_items" in updates and not isinstance(updates["line_items"], str):
        # Already parsed or updated
        merged["line_items"] = updates["line_items"]
        
    warnings = compute_warnings(merged)
    merged["warnings"] = warnings

    conn = get_connection()
    cursor = conn.cursor()

    fields_to_update = [
        "date", "vendor", "currency", "subtotal", "tax", "total",
        "payment_method", "category", "line_items", "confidence",
        "notes", "raw_model_output", "status", "warnings"
    ]
    
    set_clauses = []
    params = []
    for f in fields_to_update:
        if f in merged:
            set_clauses.append(f"{f} = ?")
            val = merged[f]
            if f in ("line_items", "warnings") and not isinstance(val, str):
                val = json.dumps(val)
            params.append(val)

    params.append(receipt_id)
    query = f"UPDATE receipts SET {', '.join(set_clauses)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return get_receipt(receipt_id)

def get_receipt(receipt_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return serialize_row(row)

def list_receipts() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM receipts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [serialize_row(r) for r in rows]

def delete_receipt(receipt_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def clear_all_receipts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM receipts")
    conn.commit()
    conn.close()
