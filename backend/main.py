import os
import csv
import io
import json
import uuid
import asyncio
import logging
from typing import List, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil

from backend import db, extractor, samples
from backend.models import ReceiptUpdate, ReceiptRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("shoebox.server")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"

# SSE broadcast queues
sse_subscribers: List[asyncio.Queue] = []
processing_queue: asyncio.Queue = asyncio.Queue()
is_worker_running = False

async def broadcast_event(event_type: str, data: dict):
    """Send SSE message to all connected clients."""
    payload = json.dumps({"event": event_type, "data": data})
    message = f"event: {event_type}\ndata: {payload}\n\n"
    dead = []
    for q in sse_subscribers:
        try:
            q.put_nowait(message)
        except Exception:
            dead.append(q)
    for d in dead:
        if d in sse_subscribers:
            sse_subscribers.remove(d)

async def sequential_worker():
    """Sequential background worker that processes one receipt at a time."""
    logger.info("Sequential extraction worker started.")
    while True:
        try:
            task = await processing_queue.get()
            receipt_id = task["id"]
            image_path = Path(task["image_path"])
            is_synthetic = task.get("is_synthetic", False)
            synthetic_fallback = task.get("synthetic_fallback")

            # Update status to scanning
            logger.info(f"Processing receipt {receipt_id} ({task['filename']})...")
            db.update_receipt(receipt_id, {"status": "scanning"})
            await broadcast_event("status_update", {
                "id": receipt_id,
                "status": "scanning",
                "filename": task["filename"]
            })

            # Call Ollama extractor
            extracted_data, status, raw_output = await extractor.extract_receipt(
                image_path=image_path,
                is_synthetic=is_synthetic,
                synthetic_fallback=synthetic_fallback
            )

            # Save updates
            update_payload = {
                **extracted_data,
                "status": status,
                "raw_model_output": raw_output
            }
            updated = db.update_receipt(receipt_id, update_payload)

            logger.info(f"Finished {receipt_id}: {status} (vendor={updated.get('vendor')}, total={updated.get('total')})")
            await broadcast_event("receipt_completed", {
                "id": receipt_id,
                "receipt": updated
            })

            processing_queue.task_done()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker error processing receipt: {e}", exc_info=True)
            try:
                if 'receipt_id' in locals():
                    updated = db.update_receipt(receipt_id, {
                        "status": "error",
                        "notes": f"Processing exception: {str(e)}"
                    })
                    await broadcast_event("receipt_completed", {
                        "id": receipt_id,
                        "receipt": updated
                    })
            except Exception:
                pass
            processing_queue.task_done()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & sample receipts
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    samples.ensure_sample_receipts()

    # Start background worker
    worker_task = asyncio.create_task(sequential_worker())
    yield
    # Cleanup
    worker_task.cancel()

app = FastAPI(title="Shoebox - Local Receipt Scanner", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & Status API
@app.get("/api/health")
async def get_health():
    """Health check verifying local Ollama and model presence."""
    status = await extractor.check_ollama_health()
    all_receipts = db.list_receipts()
    status["receipts_count"] = len(all_receipts)
    status["queue_length"] = processing_queue.qsize()
    return status

# SSE Realtime Stream
@app.get("/api/events")
async def sse_endpoint():
    """Server-Sent Events endpoint streaming sequential receipt progress."""
    q = asyncio.Queue()
    sse_subscribers.append(q)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send initial sync event
            health = await extractor.check_ollama_health()
            init_msg = json.dumps({"event": "connected", "data": {"health": health}})
            yield f"event: connected\ndata: {init_msg}\n\n"

            while True:
                msg = await q.get()
                yield msg
        except asyncio.CancelledError:
            pass
        finally:
            if q in sse_subscribers:
                sse_subscribers.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Upload & Queue Receipts
@app.post("/api/upload")
async def upload_receipts(files: List[UploadFile] = File(...)):
    """Upload multiple receipt photos and queue for sequential scanning."""
    results = []
    for file in files:
        file_id = str(uuid.uuid4())[:8]
        safe_name = f"{file_id}_{file.filename}"
        dest_path = UPLOADS_DIR / safe_name
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Initial placeholder record
        record_data = {
            "id": file_id,
            "filename": file.filename,
            "image_path": f"/uploads/{safe_name}",
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "vendor": "Processing...",
            "currency": "INR",
            "total": 0.0,
            "confidence": 0.0,
            "category": "Other",
            "line_items": [],
            "notes": None,
            "is_synthetic": False
        }
        
        saved = db.create_receipt(record_data)
        results.append(saved)

        # Put on worker queue
        await processing_queue.put({
            "id": file_id,
            "filename": file.filename,
            "image_path": str(dest_path),
            "is_synthetic": False
        })

        await broadcast_event("receipt_queued", {"receipt": saved})

    return {"uploaded": len(results), "receipts": results}

# Demo Mode: Sample Receipts
@app.post("/api/demo/samples")
async def load_sample_receipts():
    """Load the 3 bundled synthetic receipts for instant demo review."""
    sample_items = samples.ensure_sample_receipts()
    results = []

    for s in sample_items:
        file_id = f"demo_{uuid.uuid4().hex[:6]}"
        safe_name = f"{file_id}_{s['filename']}"
        dest_path = UPLOADS_DIR / safe_name
        shutil.copyfile(str(s["path"]), str(dest_path))

        record_data = {
            "id": file_id,
            "filename": s["filename"],
            "image_path": f"/uploads/{safe_name}",
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "vendor": "Scanning sample...",
            "currency": s["ground_truth"]["currency"],
            "total": 0.0,
            "confidence": 0.0,
            "category": "Other",
            "line_items": [],
            "notes": "Synthetic demo sample",
            "is_synthetic": True
        }
        
        saved = db.create_receipt(record_data)
        results.append(saved)

        await processing_queue.put({
            "id": file_id,
            "filename": s["filename"],
            "image_path": str(dest_path),
            "is_synthetic": True,
            "synthetic_fallback": s["ground_truth"]
        })

        await broadcast_event("receipt_queued", {"receipt": saved})

    return {"loaded": len(results), "receipts": results}

# Receipts CRUD
@app.get("/api/receipts")
async def list_receipts():
    return db.list_receipts()

@app.get("/api/receipts/{receipt_id}")
async def get_receipt(receipt_id: str):
    rec = db.get_receipt(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return rec

@app.patch("/api/receipts/{receipt_id}")
async def update_receipt(receipt_id: str, updates: ReceiptUpdate):
    """Inline cell editing & drawer updates with automatic math check recalculation."""
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    updated = db.update_receipt(receipt_id, update_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Receipt not found")
    await broadcast_event("receipt_updated", {"receipt": updated})
    return updated

@app.delete("/api/receipts/{receipt_id}")
async def delete_receipt(receipt_id: str):
    rec = db.get_receipt(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Remove file if exists
    img_rel = rec.get("image_path", "").replace("/uploads/", "")
    file_path = UPLOADS_DIR / img_rel
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass

    deleted = db.delete_receipt(receipt_id)
    await broadcast_event("receipt_deleted", {"id": receipt_id})
    return {"deleted": deleted, "id": receipt_id}

@app.post("/api/receipts/clear")
async def clear_all_receipts():
    db.clear_all_receipts()
    # Clean uploads directory
    for f in UPLOADS_DIR.glob("*"):
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass
    await broadcast_event("receipts_cleared", {})
    return {"message": "All receipts cleared"}

@app.post("/api/receipts/{receipt_id}/reprocess")
async def reprocess_receipt(receipt_id: str):
    rec = db.get_receipt(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    img_rel = rec.get("image_path", "").replace("/uploads/", "")
    file_path = UPLOADS_DIR / img_rel
    if not file_path.exists():
        raise HTTPException(status_code=400, detail="Image file not found on disk")

    db.update_receipt(receipt_id, {"status": "queued"})
    await processing_queue.put({
        "id": receipt_id,
        "filename": rec["filename"],
        "image_path": str(file_path),
        "is_synthetic": rec.get("is_synthetic", False)
    })
    await broadcast_event("status_update", {"id": receipt_id, "status": "queued", "filename": rec["filename"]})
    return {"status": "requeued", "id": receipt_id}

# CSV Export: Receipts
@app.get("/api/export/csv")
async def export_receipts_csv():
    """Export clean spreadsheet with BOM for seamless Excel compatibility."""
    receipts = db.list_receipts()
    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens with correct encoding and symbols
    output.write("\ufeff")

    writer = csv.writer(output)
    headers = [
        "Date", "Vendor", "Category", "Currency",
        "Subtotal", "Tax", "Total", "Payment Method",
        "Confidence", "Notes", "Warnings", "File Name", "ID"
    ]
    writer.writerow(headers)

    for r in receipts:
        warnings_str = "; ".join(r.get("warnings", []))
        writer.writerow([
            r.get("date") or "",
            r.get("vendor") or "",
            r.get("category") or "Other",
            r.get("currency") or "INR",
            f"{r['subtotal']:.2f}" if r.get("subtotal") is not None else "",
            f"{r['tax']:.2f}" if r.get("tax") is not None else "",
            f"{r['total']:.2f}" if r.get("total") is not None else "0.00",
            r.get("payment_method") or "",
            f"{r['confidence']:.2f}" if r.get("confidence") is not None else "",
            r.get("notes") or "",
            warnings_str,
            r.get("filename") or "",
            r.get("id") or ""
        ])

    csv_data = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=shoebox_receipts_{timestamp}.csv"
        }
    )

# CSV Export: Line Items
@app.get("/api/export/line-items-csv")
async def export_line_items_csv():
    """Export all individual line items with receipt metadata."""
    receipts = db.list_receipts()
    output = io.StringIO()
    output.write("\ufeff")

    writer = csv.writer(output)
    headers = [
        "Receipt ID", "Date", "Vendor", "Category",
        "Item Description", "Quantity", "Unit Price", "Total Price", "Currency"
    ]
    writer.writerow(headers)

    for r in receipts:
        items = r.get("line_items", [])
        if not items:
            # Export a single row with the main total
            writer.writerow([
                r.get("id"),
                r.get("date") or "",
                r.get("vendor") or "",
                r.get("category") or "Other",
                "Total Amount",
                1,
                f"{r['total']:.2f}" if r.get("total") is not None else "0.00",
                f"{r['total']:.2f}" if r.get("total") is not None else "0.00",
                r.get("currency") or "INR"
            ])
        else:
            for it in items:
                qty = float(it.get("qty", 1.0) or 1.0)
                price = float(it.get("price", 0.0) or 0.0)
                item_total = round(qty * price, 2)
                writer.writerow([
                    r.get("id"),
                    r.get("date") or "",
                    r.get("vendor") or "",
                    r.get("category") or "Other",
                    it.get("description", "Item"),
                    qty,
                    f"{price:.2f}",
                    f"{item_total:.2f}",
                    r.get("currency") or "INR"
                ])

    csv_data = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=shoebox_line_items_{timestamp}.csv"
        }
    )

# Static file mounts
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
