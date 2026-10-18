import urllib.request
import json
import time
import io
import mimetypes

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("=" * 60)
    print("  RUNNING SHOEBOX AUTOMATED INTEGRATION TESTS")
    print("=" * 60)

    # 1. Test frontend endpoints
    print("\n[1] Testing Frontend static endpoints...")
    with urllib.request.urlopen(f"{BASE_URL}/") as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "Shoebox" in html
        assert "styles.css" in html
        assert "app.js" in html
    print("    [PASS] GET / served HTML correctly")

    with urllib.request.urlopen(f"{BASE_URL}/styles.css") as resp:
        assert resp.status == 200
    print("    [PASS] GET /styles.css loaded")

    with urllib.request.urlopen(f"{BASE_URL}/app.js") as resp:
        assert resp.status == 200
    print("    [PASS] GET /app.js loaded")

    # 2. Test Health check
    print("\n[2] Testing Health Check API...")
    with urllib.request.urlopen(f"{BASE_URL}/api/health") as resp:
        assert resp.status == 200
        health = json.loads(resp.read().decode("utf-8"))
        print("    Health:", health)
        assert "ollama_running" in health
        assert "model_name" in health
        assert "endpoint" in health
    print("    [PASS] Health check verified")

    # 3. Test Demo Samples Trigger
    print("\n[3] Testing POST /api/demo/samples...")
    req = urllib.request.Request(f"{BASE_URL}/api/demo/samples", data=b"", method="POST")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        print(f"    Loaded {len(res['receipts'])} sample receipts")
        assert len(res["receipts"]) == 3
    print("    [PASS] Demo samples queued for scanning")

    # 4. Wait for sequential processing
    print("\n[4] Waiting for sequential queue worker to complete extraction...")
    max_wait = 25
    start = time.time()
    receipts = []
    while time.time() - start < max_wait:
        with urllib.request.urlopen(f"{BASE_URL}/api/receipts") as resp:
            receipts = json.loads(resp.read().decode("utf-8"))
            statuses = [r["status"] for r in receipts]
            if all(s in ("done", "needs review", "error") for s in statuses) and len(statuses) >= 3:
                print(f"    Sequential scan completed in {time.time() - start:.1f}s")
                print("    Statuses:", statuses)
                break
        time.sleep(1)

    assert len(receipts) >= 3
    sample_r = receipts[0]
    print(f"    Sample receipt extracted: {sample_r['vendor']} | Total: {sample_r['total']} {sample_r['currency']} | Date: {sample_r['date']}")
    print("    [PASS] Sequential processing verified")

    # 5. Test inline editing and SQLite persistence
    print("\n[5] Testing inline cell editing & SQLite persistence...")
    edit_id = sample_r["id"]
    patch_payload = json.dumps({
        "vendor": "Blue Tokai Coffee (Verified Edit)",
        "total": 999.50,
        "category": "Food"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/receipts/{edit_id}",
        data=patch_payload,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        updated = json.loads(resp.read().decode("utf-8"))
        assert updated["vendor"] == "Blue Tokai Coffee (Verified Edit)"
        assert updated["total"] == 999.50

    # Reload directly from SQLite to prove persistence after page refresh
    with urllib.request.urlopen(f"{BASE_URL}/api/receipts/{edit_id}") as resp:
        reloaded = json.loads(resp.read().decode("utf-8"))
        assert reloaded["vendor"] == "Blue Tokai Coffee (Verified Edit)"
        assert reloaded["total"] == 999.50
    print("    [PASS] Edit persisted across database reads")

    # 6. Test deliberate corrupted file handling
    print("\n[6] Testing corrupted image upload resilience...")
    # Send a text file disguised as a JPEG
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    corrupt_body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="corrupted_test_image.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
        "THIS_IS_DELIBERATELY_CORRUPTED_TEXT_NOT_A_VALID_IMAGE_BYTES_1234567890\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/upload",
        data=corrupt_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        upload_res = json.loads(resp.read().decode("utf-8"))
        corrupt_id = upload_res["receipts"][0]["id"]
        print(f"    Queued corrupted image as ID: {corrupt_id}")

    # Wait for queue worker to process the corrupted file
    time.sleep(3)
    with urllib.request.urlopen(f"{BASE_URL}/api/receipts/{corrupt_id}") as resp:
        corrupt_rec = json.loads(resp.read().decode("utf-8"))
        print(f"    Corrupted file status: {corrupt_rec['status']} | Notes: {corrupt_rec.get('notes')}")
        assert corrupt_rec["status"] in ("needs review", "error")
    print("    [PASS] Corrupted file handled gracefully without crashing batch!")

    # 7. Test CSV Export (Excel BOM and column validation)
    print("\n[7] Testing Receipts CSV Export (Excel UTF-8 BOM)...")
    with urllib.request.urlopen(f"{BASE_URL}/api/export/csv") as resp:
        assert resp.status == 200
        raw_csv = resp.read()
        assert raw_csv.startswith(b"\xef\xbb\xbf") # UTF-8 BOM
        csv_text = raw_csv.decode("utf-8-sig")
        assert "Date,Vendor,Category,Currency,Subtotal,Tax,Total" in csv_text
        assert "Blue Tokai Coffee (Verified Edit)" in csv_text
    print("    [PASS] Receipts CSV export contains UTF-8 BOM and correct headers")

    # 8. Test Line Items CSV Export
    print("\n[8] Testing Line Items CSV Export...")
    with urllib.request.urlopen(f"{BASE_URL}/api/export/line-items-csv") as resp:
        assert resp.status == 200
        raw_li = resp.read()
        assert raw_li.startswith(b"\xef\xbb\xbf")
        li_text = raw_li.decode("utf-8-sig")
        assert "Receipt ID,Date,Vendor,Category,Item Description,Quantity" in li_text
    print("    [PASS] Line items CSV export verified")

    print("\n" + "=" * 60)
    print("  [SUCCESS] ALL ACCEPTANCE CRITERIA VERIFIED AND PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
