import asyncio
import os
import sys
import json
from pathlib import Path
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = Path(__file__).resolve().parent
CLIPS_DIR = VIDEO_DIR / "clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_RECEIPTS_DIR = PROJECT_ROOT / "demo_receipts"

CURSOR_SCRIPT = """
(function() {
  if (document.getElementById('demo-cursor')) return;
  const cursor = document.createElement('div');
  cursor.id = 'demo-cursor';
  cursor.style.cssText = `
    position: fixed;
    top: 0; left: 0;
    width: 22px; height: 22px;
    background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(220,225,255,0.9) 100%);
    border: 2px solid rgba(15, 23, 42, 0.9);
    border-radius: 50%;
    pointer-events: none;
    z-index: 999999;
    box-shadow: 0 0 16px rgba(99, 102, 241, 0.7);
    transition: transform 0.05s ease-out;
    transform: translate(-100px, -100px);
  `;
  document.body.appendChild(cursor);

  window.__moveCursor = function(x, y) {
    cursor.style.transform = `translate(${x}px, ${y}px)`;
  };

  window.__clickRipple = function(x, y) {
    const ripple = document.createElement('div');
    ripple.className = 'click-ripple';
    ripple.style.cssText = `
      position: fixed;
      top: ${y}px; left: ${x}px;
      width: 10px; height: 10px;
      border: 2px solid #818CF8;
      border-radius: 50%;
      pointer-events: none;
      z-index: 999998;
      animation: rippleAnim 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      transform: translate(-50%, -50%);
    `;
    document.body.appendChild(ripple);
    setTimeout(() => ripple.remove(), 480);
  };

  const style = document.createElement('style');
  style.textContent = `
    @keyframes rippleAnim {
      0%   { width: 10px; height: 10px; opacity: 1; border-color: #A5B4FC; }
      100% { width: 56px; height: 56px; opacity: 0; border-color: #6366F1; }
    }
  `;
  document.head.appendChild(style);
})();
"""

async def smooth_move(page, start_x, start_y, end_x, end_y, steps=24):
    for i in range(steps + 1):
        t = i / steps
        # smooth cubic ease
        ease = 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
        cur_x = start_x + (end_x - start_x) * ease
        cur_y = start_y + (end_y - start_y) * ease
        await page.evaluate(f"window.__moveCursor({cur_x}, {cur_y})")
        await asyncio.sleep(0.016)

async def smooth_click(page, x, y):
    await page.evaluate(f"window.__clickRipple({x}, {y})")
    await asyncio.sleep(0.08)

async def record_all_clips():
    print("Starting Playwright cinematic recording pipeline...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1920,1080",
                "--hide-scrollbars"
            ]
        )

        # ----------------------------------------------------
        # Scene 4: Proof (Privacy Badge & Expandable Proof Panel)
        # ----------------------------------------------------
        print("\n[Recording] Scene 4: Privacy Proof Panel...")
        proof_clip_dir = CLIPS_DIR / "raw_scene_04"
        proof_clip_dir.mkdir(parents=True, exist_ok=True)
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(proof_clip_dir),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(CURSOR_SCRIPT)

        # Dismiss setup modal if open to show clean app
        await page.evaluate("""
            const modal = document.getElementById('setupHelperModal');
            if (modal) modal.style.display = 'none';
        """)

        await asyncio.sleep(1.0)
        # Initial cursor at bottom right
        cx, cy = 1200, 700
        await page.evaluate(f"window.__moveCursor({cx}, {cy})")
        await asyncio.sleep(0.6)

        # Move to Privacy Badge
        badge_box = await page.locator("#privacyBadgeBtn").bounding_box()
        bx = badge_box["x"] + badge_box["width"] / 2
        by = badge_box["y"] + badge_box["height"] / 2
        await smooth_move(page, cx, cy, bx, by, steps=30)
        cx, cy = bx, by
        await asyncio.sleep(0.3)
        await smooth_click(page, bx, by)
        await page.locator("#privacyBadgeBtn").click()

        # Hover over Proof Stats
        await asyncio.sleep(1.2)
        model_box = await page.locator("#proofModel").bounding_box()
        if model_box:
            await smooth_move(page, cx, cy, model_box["x"] + 30, model_box["y"] + 10, steps=25)
            cx, cy = model_box["x"] + 30, model_box["y"] + 10
            await asyncio.sleep(1.5)

        time_box = await page.locator("#proofTimeSaved").bounding_box()
        if time_box:
            await smooth_move(page, cx, cy, time_box["x"] + 40, time_box["y"] + 10, steps=20)
            cx, cy = time_box["x"] + 40, time_box["y"] + 10
            await asyncio.sleep(1.5)

        await asyncio.sleep(1.2)
        await page.close()
        await context.close()
        print("  [OK] Scene 4 recorded.")

        # ----------------------------------------------------
        # Scene 5: Magic Extraction (Drag & Drop + Streaming Scan)
        # ----------------------------------------------------
        print("\n[Recording] Scene 5: Magic Extraction & Real-time Scan...")
        magic_clip_dir = CLIPS_DIR / "raw_scene_05"
        magic_clip_dir.mkdir(parents=True, exist_ok=True)
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(magic_clip_dir),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(CURSOR_SCRIPT)
        await page.evaluate("""
            const modal = document.getElementById('setupHelperModal');
            if (modal) modal.style.display = 'none';
        """)

        # Clear any existing receipts for clean hero demo
        await page.request.post("http://127.0.0.1:8000/api/receipts/clear")
        await page.reload()
        await page.evaluate(CURSOR_SCRIPT)
        await page.evaluate("const m = document.getElementById('setupHelperModal'); if (m) m.style.display = 'none';")

        await asyncio.sleep(0.8)
        cx, cy = 960, 200
        await page.evaluate(f"window.__moveCursor({cx}, {cy})")

        # Move to Dropzone
        drop_box = await page.locator("#dropzone").bounding_box()
        dx = drop_box["x"] + drop_box["width"] / 2
        dy = drop_box["y"] + drop_box["height"] / 2 - 20
        await smooth_move(page, cx, cy, dx, dy, steps=28)
        cx, cy = dx, dy
        await asyncio.sleep(0.4)

        # Upload the 4 receipts from demo_receipts
        files_to_upload = [
            str(DEMO_RECEIPTS_DIR / "receipt_01_cafe.png"),
            str(DEMO_RECEIPTS_DIR / "receipt_02_tech.png"),
            str(DEMO_RECEIPTS_DIR / "receipt_03_travel.png"),
            str(DEMO_RECEIPTS_DIR / "receipt_04_software.png")
        ]
        
        file_input = page.locator("#fileInput")
        await file_input.set_input_files(files_to_upload)
        await smooth_click(page, dx, dy)

        # Watch scanning beam sweep and rows appear
        await asyncio.sleep(1.5)
        # Move cursor gently to the side
        await smooth_move(page, cx, cy, 1400, 480, steps=30)
        cx, cy = 1400, 480

        # Wait for all 4 receipts to finish processing
        max_wait = 25
        for _ in range(max_wait):
            done_rows = await page.locator("#receiptsTableBody tr").count()
            if done_rows >= 4:
                break
            await asyncio.sleep(1.0)

        # Highlight summary numbers counting up
        stat_box = await page.locator("#statTotalSpend").bounding_box()
        if stat_box:
            await smooth_move(page, cx, cy, stat_box["x"] + 60, stat_box["y"] + 20, steps=24)
            cx, cy = stat_box["x"] + 60, stat_box["y"] + 20
            await asyncio.sleep(1.8)

        await page.close()
        await context.close()
        print("  [OK] Scene 5 recorded.")

        # ----------------------------------------------------
        # Scene 6: Trust & Review (Amber Row & Side Drawer)
        # ----------------------------------------------------
        print("\n[Recording] Scene 6: Amber Warning & Side Drawer...")
        trust_clip_dir = CLIPS_DIR / "raw_scene_06"
        trust_clip_dir.mkdir(parents=True, exist_ok=True)
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(trust_clip_dir),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(CURSOR_SCRIPT)
        await page.evaluate("const m = document.getElementById('setupHelperModal'); if (m) m.style.display = 'none';")

        await asyncio.sleep(1.0)
        # Locate the amber or top row
        first_row = page.locator("#receiptsTableBody tr").first
        await first_row.wait_for()
        r_box = await first_row.bounding_box()

        cx, cy = 600, 300
        await page.evaluate(f"window.__moveCursor({cx}, {cy})")
        rx = r_box["x"] + r_box["width"] * 0.4
        ry = r_box["y"] + r_box["height"] / 2
        await smooth_move(page, cx, cy, rx, ry, steps=28)
        cx, cy = rx, ry
        await asyncio.sleep(0.4)

        # Click row to open Drawer
        await smooth_click(page, rx, ry)
        await first_row.click()

        # Drawer slides in with spring curve
        await asyncio.sleep(1.2)
        # Inspect form fields
        vendor_input = page.locator("#drawerVendorInput")
        v_box = await vendor_input.bounding_box()
        if v_box:
            await smooth_move(page, cx, cy, v_box["x"] + 100, v_box["y"] + 15, steps=22)
            cx, cy = v_box["x"] + 100, v_box["y"] + 15
            await asyncio.sleep(0.6)

        # Move to Save Changes button
        save_btn = page.locator("#saveDrawerBtn")
        s_box = await save_btn.bounding_box()
        if s_box:
            sbx = s_box["x"] + s_box["width"] / 2
            sby = s_box["y"] + s_box["height"] / 2
            await smooth_move(page, cx, cy, sbx, sby, steps=24)
            cx, cy = sbx, sby
            await asyncio.sleep(0.3)
            await smooth_click(page, sbx, sby)
            await save_btn.click()

        # Toast notification appears
        await asyncio.sleep(1.5)
        await page.close()
        await context.close()
        print("  [OK] Scene 6 recorded.")

        # ----------------------------------------------------
        # Scene 7: Output & Excel CSV Export
        # ----------------------------------------------------
        print("\n[Recording] Scene 7: Export Spreadsheet...")
        export_clip_dir = CLIPS_DIR / "raw_scene_07"
        export_clip_dir.mkdir(parents=True, exist_ok=True)
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(export_clip_dir),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")
        await page.evaluate(CURSOR_SCRIPT)
        await page.evaluate("const m = document.getElementById('setupHelperModal'); if (m) m.style.display = 'none';")

        await asyncio.sleep(1.0)
        cx, cy = 1000, 400
        await page.evaluate(f"window.__moveCursor({cx}, {cy})")

        # Move to Export Dropdown
        exp_btn = page.locator("#exportMenuBtn")
        eb_box = await exp_btn.bounding_box()
        ex = eb_box["x"] + eb_box["width"] / 2
        ey = eb_box["y"] + eb_box["height"] / 2
        await smooth_move(page, cx, cy, ex, ey, steps=26)
        cx, cy = ex, ey
        await asyncio.sleep(0.3)
        await smooth_click(page, ex, ey)
        await exp_btn.click()

        # Dropdown opens
        await asyncio.sleep(0.6)
        csv_item = page.locator("#exportReceiptsCsv")
        ci_box = await csv_item.bounding_box()
        cix = ci_box["x"] + ci_box["width"] / 2
        ciy = ci_box["y"] + ci_box["height"] / 2
        await smooth_move(page, cx, cy, cix, ciy, steps=20)
        cx, cy = cix, ciy
        await asyncio.sleep(0.3)
        await smooth_click(page, cix, ciy)
        await csv_item.click()

        # Toast appears
        await asyncio.sleep(2.0)
        await page.close()
        await context.close()
        print("  [OK] Scene 7 recorded.")

        await browser.close()

    print("\nAll raw footage clips recorded successfully into video/clips/")

if __name__ == "__main__":
    asyncio.run(record_all_clips())
