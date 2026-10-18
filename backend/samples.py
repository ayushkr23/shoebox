import os
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"

def get_font(size: int, font_type: str = "regular"):
    """Get system font or fallback to default."""
    candidates = []
    if font_type == "mono":
        candidates = ["cour.ttf", "consola.ttf", "Courier New.ttf", "DejaVuSansMono.ttf"]
    elif font_type == "hand":
        candidates = ["comic.ttf", "segoeprb.ttf", "segoesc.ttf", "Inkfree.ttf", "arial.ttf"]
    elif font_type == "bold":
        candidates = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "Helvetica-Bold.ttf"]
    else:
        candidates = ["arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf"]

    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def create_sample_clean_cafe(dest_path: Path) -> Path:
    """Generate sample 1: Clean modern cafe receipt with Indian GST."""
    w, h = 600, 850
    img = Image.new("RGB", (w, h), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)

    f_title = get_font(26, "bold")
    f_header = get_font(18, "bold")
    f_body = get_font(16, "mono")
    f_body_bold = get_font(16, "bold")
    f_small = get_font(13, "mono")

    # Header badge
    draw.rectangle([(20, 15), (580, 45)], fill=(238, 242, 255), outline=(199, 210, 254), width=1)
    draw.text((300, 30), "*** SYNTHETIC RECEIPT (DEMO) ***", fill=(99, 102, 241), font=f_small, anchor="mm")

    # Cafe Name & Info
    y = 75
    draw.text((300, y), "BLUE TOKAI COFFEE ROASTERS", fill=(20, 20, 25), font=f_title, anchor="mm")
    y += 32
    draw.text((300, y), "Indiranagar 100ft Road, Bengaluru 560038", fill=(80, 80, 90), font=f_small, anchor="mm")
    y += 20
    draw.text((300, y), "GSTIN: 29AABCU9603R1ZM | Tel: +91 80 4123 9876", fill=(90, 90, 100), font=f_small, anchor="mm")
    y += 28

    # Dashed divider
    draw.line([(30, y), (570, y)], fill=(180, 180, 185), width=1)
    y += 20

    # Date and order metadata
    draw.text((40, y), "Date: 2026-03-14", fill=(30, 30, 35), font=f_body)
    draw.text((560, y), "Time: 14:22:10", fill=(30, 30, 35), font=f_body, anchor="ra")
    y += 24
    draw.text((40, y), "Order #BT-4892", fill=(40, 40, 45), font=f_body)
    draw.text((560, y), "Table: 04 (Dine In)", fill=(40, 40, 45), font=f_body, anchor="ra")
    y += 28

    # Table header
    draw.line([(30, y), (570, y)], fill=(180, 180, 185), width=1)
    y += 12
    draw.text((40, y), "ITEM", fill=(100, 100, 110), font=f_small)
    draw.text((340, y), "QTY", fill=(100, 100, 110), font=f_small, anchor="ra")
    draw.text((440, y), "RATE", fill=(100, 100, 110), font=f_small, anchor="ra")
    draw.text((560, y), "AMOUNT", fill=(100, 100, 110), font=f_small, anchor="ra")
    y += 22
    draw.line([(30, y), (570, y)], fill=(210, 210, 215), width=1)
    y += 20

    # Line items
    items = [
        ("Sea Salt Mocha (Large)", 1, 260.00, 260.00),
        ("Butter Croissant", 1, 170.00, 170.00),
    ]

    for desc, qty, rate, amt in items:
        draw.text((40, y), desc, fill=(25, 25, 30), font=f_body_bold)
        draw.text((340, y), str(qty), fill=(25, 25, 30), font=f_body, anchor="ra")
        draw.text((440, y), f"{rate:.2f}", fill=(25, 25, 30), font=f_body, anchor="ra")
        draw.text((560, y), f"Rs. {amt:.2f}", fill=(25, 25, 30), font=f_body, anchor="ra")
        y += 32

    y += 10
    draw.line([(30, y), (570, y)], fill=(180, 180, 185), width=1)
    y += 20

    # Subtotals & Tax
    draw.text((320, y), "Subtotal:", fill=(50, 50, 55), font=f_body)
    draw.text((560, y), "INR 430.00", fill=(50, 50, 55), font=f_body, anchor="ra")
    y += 26
    draw.text((320, y), "CGST (2.5%):", fill=(70, 70, 80), font=f_small)
    draw.text((560, y), "INR 10.75", fill=(70, 70, 80), font=f_small, anchor="ra")
    y += 22
    draw.text((320, y), "SGST (2.5%):", fill=(70, 70, 80), font=f_small)
    draw.text((560, y), "INR 10.75", fill=(70, 70, 80), font=f_small, anchor="ra")
    y += 28

    draw.line([(310, y), (570, y)], fill=(100, 100, 100), width=2)
    y += 18

    # Grand Total
    draw.text((300, y), "TOTAL AMOUNT:", fill=(15, 15, 20), font=f_header)
    draw.text((560, y), "INR 451.50", fill=(15, 15, 20), font=f_header, anchor="ra")
    y += 40

    # Payment details
    draw.rectangle([(40, y), (560, y + 45)], fill=(245, 245, 248), outline=(225, 225, 230), width=1)
    draw.text((55, y + 14), "Payment Mode: UPI (GPay)", fill=(40, 40, 45), font=f_small)
    draw.text((545, y + 14), "Ref: UPI/60731849201", fill=(40, 40, 45), font=f_small, anchor="ra")
    y += 75

    # Footer barcode simulation
    draw.text((300, y), "Thank you for brewing with us! Have a great day.", fill=(110, 110, 120), font=f_small, anchor="mm")
    y += 24
    for bx in range(120, 480, 4):
        bw = random.choice([1, 2, 3])
        draw.line([(bx, y), (bx, y + 36)], fill=(50, 50, 60), width=bw)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest_path), "PNG", quality=95)
    return dest_path

def create_sample_crumpled_tech(dest_path: Path) -> Path:
    """Generate sample 2: Crumpled receipt with slight angle, creases, and noise."""
    w, h = 640, 920
    # Base paper image with pale off-white / thermal grayish yellow
    base = Image.new("RGBA", (w, h), color=(244, 242, 236, 255))
    draw = ImageDraw.Draw(base)

    f_title = get_font(24, "bold")
    f_header = get_font(18, "bold")
    f_body = get_font(15, "mono")
    f_body_bold = get_font(15, "bold")
    f_small = get_font(12, "mono")

    # Demo Banner
    draw.rectangle([(30, 20), (610, 50)], fill=(254, 243, 199), outline=(245, 158, 11), width=1)
    draw.text((320, 35), "*** SYNTHETIC RECEIPT (DEMO) ***", fill=(180, 83, 9), font=f_small, anchor="mm")

    y = 75
    draw.text((320, y), "SILICON HARDWARE HUB", fill=(30, 30, 30), font=f_title, anchor="mm")
    y += 28
    draw.text((320, y), "Shop 14, Nehru Place Market, New Delhi 110019", fill=(70, 70, 70), font=f_small, anchor="mm")
    y += 18
    draw.text((320, y), "GSTIN: 07AAACH7491D1Z4 | Ph: 011-26418899", fill=(80, 80, 80), font=f_small, anchor="mm")
    y += 24

    draw.line([(40, y), (600, y)], fill=(160, 160, 160), width=1)
    y += 18

    draw.text((50, y), "Invoice: SHH-10829", fill=(30, 30, 30), font=f_body)
    draw.text((590, y), "Date: 2026-02-28", fill=(30, 30, 30), font=f_body, anchor="ra")
    y += 22
    draw.text((50, y), "Customer: Cash / Walk-in", fill=(60, 60, 60), font=f_small)
    draw.text((590, y), "Category: Equipment / Supplies", fill=(60, 60, 60), font=f_small, anchor="ra")
    y += 26

    # Header
    draw.line([(40, y), (600, y)], fill=(160, 160, 160), width=1)
    y += 12
    draw.text((50, y), "PARTICULARS", fill=(90, 90, 90), font=f_small)
    draw.text((380, y), "QTY", fill=(90, 90, 90), font=f_small, anchor="ra")
    draw.text((470, y), "PRICE", fill=(90, 90, 90), font=f_small, anchor="ra")
    draw.text((590, y), "TOTAL", fill=(90, 90, 90), font=f_small, anchor="ra")
    y += 20
    draw.line([(40, y), (600, y)], fill=(200, 200, 200), width=1)
    y += 18

    # 3 line items
    items = [
        ("7-in-1 USB-C Hub Aluminium", 1, 2100.00, 2100.00),
        ("Braided 4K HDMI Cable 2M", 1, 450.00, 450.00),
        ("Thermal Paste Arctic MX-4 4g", 1, 399.00, 399.00)
    ]
    for desc, qty, pr, tot in items:
        draw.text((50, y), desc, fill=(35, 35, 35), font=f_body_bold)
        draw.text((380, y), str(qty), fill=(35, 35, 35), font=f_body, anchor="ra")
        draw.text((470, y), f"{pr:.2f}", fill=(35, 35, 35), font=f_body, anchor="ra")
        draw.text((590, y), f"Rs. {tot:.2f}", fill=(35, 35, 35), font=f_body, anchor="ra")
        y += 30

    y += 10
    draw.line([(40, y), (600, y)], fill=(160, 160, 160), width=1)
    y += 20

    # Subtotal and 18% GST
    draw.text((360, y), "Subtotal:", fill=(60, 60, 60), font=f_body)
    draw.text((590, y), "INR 2949.00", fill=(60, 60, 60), font=f_body, anchor="ra")
    y += 24
    draw.text((360, y), "GST (18%):", fill=(70, 70, 70), font=f_body)
    draw.text((590, y), "INR 530.82", fill=(70, 70, 70), font=f_body, anchor="ra")
    y += 28
    draw.line([(340, y), (600, y)], fill=(60, 60, 60), width=2)
    y += 16
    draw.text((330, y), "NET TOTAL:", fill=(20, 20, 20), font=f_header)
    draw.text((590, y), "INR 3479.82", fill=(20, 20, 20), font=f_header, anchor="ra")
    y += 34
    draw.text((590, y), "(Rounded to Rs. 3,480.00)", fill=(100, 100, 100), font=f_small, anchor="ra")
    y += 40

    draw.text((50, y), "Payment: Business Debit Card (Visa Ending 8812)", fill=(60, 60, 60), font=f_small)
    y += 22
    draw.text((50, y), "Warranty: 1 Year Manufacturer Warranty on Hub", fill=(90, 90, 90), font=f_small)
    y += 40

    # Simulated Crumple & Paper Creases
    crease_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(crease_overlay)

    creases = [
        ((20, 180), (620, 240)),
        ((10, 420), (630, 390)),
        ((30, 660), (600, 710)),
        ((150, 40), (220, 880)),
        ((460, 30), (410, 890)),
    ]
    for p1, p2 in creases:
        # Dark shadow side
        c_draw.line([p1, p2], fill=(40, 35, 30, 40), width=3)
        # Highlight side
        c_draw.line([(p1[0] + 2, p1[1] + 2), (p2[0] + 2, p2[1] + 2)], fill=(255, 255, 255, 60), width=2)

    # Combine creases
    composite = Image.alpha_composite(base, crease_overlay)

    # Add subtle thermal paper noise
    noise = Image.effect_noise((w, h), 4.0)
    noise_rgba = noise.convert("RGBA")
    # Blend gently
    composite = Image.blend(composite.convert("RGB"), noise_rgba.convert("RGB"), 0.03)

    # Rotate slightly (1.8 degrees) to give crumpled/realistic scanned feel
    rotated = composite.rotate(1.8, resample=Image.BICUBIC, expand=True, fillcolor=(235, 233, 227))

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    rotated.save(str(dest_path), "PNG", quality=95)
    return dest_path

def create_sample_handwritten_freelance(dest_path: Path) -> Path:
    """Generate sample 3: Handwritten-style freelance travel receipt/bill with stamp."""
    w, h = 640, 800
    img = Image.new("RGB", (w, h), color=(255, 253, 248))
    draw = ImageDraw.Draw(img)

    f_title = get_font(24, "bold")
    f_sub = get_font(16, "bold")
    f_hand = get_font(18, "hand")
    f_hand_bold = get_font(20, "hand")
    f_small = get_font(13, "regular")

    # Demo Banner
    draw.rectangle([(30, 15), (610, 45)], fill=(254, 226, 226), outline=(239, 68, 68), width=1)
    draw.text((320, 30), "*** SYNTHETIC RECEIPT (DEMO) ***", fill=(185, 28, 28), font=f_small, anchor="mm")

    # Header Box
    y = 65
    draw.rectangle([(30, y), (610, y + 105)], outline=(30, 50, 100), width=2)
    draw.text((320, y + 22), "RAMESH TRAVELS & CAB SERVICES", fill=(20, 40, 90), font=f_title, anchor="mm")
    draw.text((320, y + 52), "All Maharashtra Tours & Airport Taxi Services", fill=(60, 70, 90), font=f_sub, anchor="mm")
    draw.text((320, y + 80), "Sahar Road, Andheri East, Mumbai 400069 | Mob: 98201-99882", fill=(80, 80, 100), font=f_small, anchor="mm")
    y += 125

    # Invoice / Receipt No and Date
    draw.text((40, y), "Receipt No: 412", fill=(20, 20, 20), font=f_sub)
    draw.text((400, y), "Date: 2026-03-02", fill=(10, 30, 130), font=f_hand_bold)
    y += 35

    draw.text((40, y), "Received from: Ayush / Client Project", fill=(20, 40, 120), font=f_hand)
    y += 30
    draw.text((40, y), "Vehicle No: MH-02-EE-4180 (Sedan)", fill=(20, 40, 120), font=f_hand)
    y += 35

    # Main handwritten table
    table_top = y
    table_bottom = y + 260
    draw.rectangle([(30, table_top), (610, table_bottom)], outline=(30, 50, 100), width=2)

    # Column lines
    draw.line([(30, table_top + 35), (610, table_top + 35)], fill=(30, 50, 100), width=2)
    draw.line([(440, table_top), (440, table_bottom)], fill=(30, 50, 100), width=2)

    draw.text((230, table_top + 18), "DESCRIPTION / PARTICULARS", fill=(20, 30, 70), font=f_sub, anchor="mm")
    draw.text((525, table_top + 18), "AMOUNT (Rs.)", fill=(20, 30, 70), font=f_sub, anchor="mm")

    # Handwritten entries
    row_y = table_top + 55
    entries = [
        ("Airport T2 Drop from Bandra BKC", "950.00"),
        ("Sea Link & Expressway Toll Charges", "120.00"),
        ("Late Night Waiting Surcharge", "180.00"),
    ]
    for desc, amt in entries:
        draw.text((50, row_y), desc, fill=(15, 30, 140), font=f_hand)
        draw.text((580, row_y), amt, fill=(15, 30, 140), font=f_hand_bold, anchor="ra")
        row_y += 45
        draw.line([(30, row_y - 8), (610, row_y - 8)], fill=(200, 210, 230), width=1)

    # Total row
    draw.line([(30, table_bottom - 45), (610, table_bottom - 45)], fill=(30, 50, 100), width=2)
    draw.text((360, table_bottom - 22), "TOTAL:", fill=(20, 20, 20), font=f_title, anchor="ra")
    draw.text((580, table_bottom - 24), "Rs. 1,250.00", fill=(10, 30, 140), font=f_hand_bold, anchor="ra")

    y = table_bottom + 25

    # Notes & Signature
    draw.text((40, y), "Payment: Cash in hand (Full & Final)", fill=(30, 30, 30), font=f_small)
    draw.text((40, y + 22), "Notes: Duty complete. Client travel reimbursement.", fill=(80, 80, 80), font=f_small)

    draw.text((520, y + 20), "Ramesh K.", fill=(15, 35, 145), font=f_hand_bold, anchor="mm")
    draw.line([(450, y + 36), (590, y + 36)], fill=(50, 50, 50), width=1)
    draw.text((520, y + 46), "(Authorized Driver)", fill=(80, 80, 80), font=f_small, anchor="mm")

    # Stamped circular "PAID" mark in reddish-magenta ink
    stamp_center = (250, y + 25)
    stamp_r = 45
    draw.ellipse(
        [(stamp_center[0] - stamp_r, stamp_center[1] - stamp_r),
         (stamp_center[0] + stamp_r, stamp_center[1] + stamp_r)],
        outline=(190, 24, 93), width=3
    )
    draw.text((stamp_center[0], stamp_center[1] - 8), "PAID", fill=(190, 24, 93), font=f_title, anchor="mm")
    draw.text((stamp_center[0], stamp_center[1] + 16), "02 MAR 2026", fill=(190, 24, 93), font=f_small, anchor="mm")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(dest_path), "PNG", quality=95)
    return dest_path

def ensure_sample_receipts() -> list[dict]:
    """Ensure the 3 bundled synthetic samples exist and return their paths and ground truth metadata."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    
    samples = [
        {
            "filename": "sample_clean_cafe.png",
            "path": SAMPLES_DIR / "sample_clean_cafe.png",
            "generator": create_sample_clean_cafe,
            "ground_truth": {
                "date": "2026-03-14",
                "vendor": "Blue Tokai Coffee Roasters",
                "currency": "INR",
                "subtotal": 430.00,
                "tax": 21.50,
                "total": 451.50,
                "category": "Food",
                "payment_method": "UPI",
                "line_items": [
                    {"description": "Sea Salt Mocha (Large)", "qty": 1.0, "price": 260.00},
                    {"description": "Butter Croissant", "qty": 1.0, "price": 170.00}
                ]
            }
        },
        {
            "filename": "sample_crumpled_tech.png",
            "path": SAMPLES_DIR / "sample_crumpled_tech.png",
            "generator": create_sample_crumpled_tech,
            "ground_truth": {
                "date": "2026-02-28",
                "vendor": "Silicon Hardware Hub",
                "currency": "INR",
                "subtotal": 2949.00,
                "tax": 530.82,
                "total": 3479.82,
                "category": "Equipment",
                "payment_method": "Visa Debit Card",
                "line_items": [
                    {"description": "7-in-1 USB-C Hub Aluminium", "qty": 1.0, "price": 2100.00},
                    {"description": "Braided 4K HDMI Cable 2M", "qty": 1.0, "price": 450.00},
                    {"description": "Thermal Paste Arctic MX-4 4g", "qty": 1.0, "price": 399.00}
                ]
            }
        },
        {
            "filename": "sample_handwritten_freelance.png",
            "path": SAMPLES_DIR / "sample_handwritten_freelance.png",
            "generator": create_sample_handwritten_freelance,
            "ground_truth": {
                "date": "2026-03-02",
                "vendor": "Ramesh Travels & Cab Services",
                "currency": "INR",
                "subtotal": 1250.00,
                "tax": 0.00,
                "total": 1250.00,
                "category": "Travel",
                "payment_method": "Cash",
                "line_items": [
                    {"description": "Airport T2 Drop from Bandra BKC", "qty": 1.0, "price": 950.00},
                    {"description": "Sea Link & Expressway Toll Charges", "qty": 1.0, "price": 120.00},
                    {"description": "Late Night Waiting Surcharge", "qty": 1.0, "price": 180.00}
                ]
            }
        }
    ]

    for item in samples:
        if not item["path"].exists():
            item["generator"](item["path"])

    return samples

if __name__ == "__main__":
    generated = ensure_sample_receipts()
    print(f"Generated {len(generated)} synthetic sample receipts in {SAMPLES_DIR}")
