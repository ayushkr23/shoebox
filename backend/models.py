from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import re
from datetime import datetime

ALLOWED_CATEGORIES = [
    "Food",
    "Travel",
    "Supplies",
    "Utilities",
    "Rent",
    "Software",
    "Equipment",
    "Services",
    "Other"
]

def clean_numeric(val: any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r"[^\d.-]", "", val.strip())
        if not cleaned or cleaned == "-" or cleaned == ".":
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def normalize_date(val: any) -> Optional[str]:
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    if not val or val.lower() in ("null", "none", "unknown", "n/a"):
        return None
    
    # Try ISO YYYY-MM-DD
    iso_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", val)
    if iso_match:
        y, m, d = iso_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    
    # Try Indian / European DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", val)
    if dmy_match:
        d, m, y = dmy_match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    # Try common formats like 12-Oct-2023 or Oct 12, 2023
    for fmt in ("%d-%b-%Y", "%d/%b/%Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
        try:
            parsed = datetime.strptime(val, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return val[:10]  # Fallback truncated string

class LineItem(BaseModel):
    description: str = Field(default="Item")
    qty: float = Field(default=1.0)
    price: float = Field(default=0.0)

    @field_validator("qty", mode="before")
    @classmethod
    def validate_qty(cls, v):
        res = clean_numeric(v)
        return res if res is not None and res > 0 else 1.0

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        res = clean_numeric(v)
        return res if res is not None else 0.0

    @field_validator("description", mode="before")
    @classmethod
    def validate_desc(cls, v):
        if not v or not str(v).strip():
            return "Item"
        return str(v).strip()

class ReceiptExtraction(BaseModel):
    date: Optional[str] = None
    vendor: str = Field(default="Unknown Vendor")
    currency: str = Field(default="INR")
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float = Field(default=0.0)
    payment_method: Optional[str] = None
    category: str = Field(default="Other")
    line_items: List[LineItem] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: Optional[str] = None

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v):
        return normalize_date(v)

    @field_validator("vendor", mode="before")
    @classmethod
    def validate_vendor(cls, v):
        if not v or not str(v).strip():
            return "Unknown Vendor"
        return str(v).strip()

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v):
        if not v:
            return "INR"
        s = str(v).strip().upper()
        if "₹" in s or "RS" in s or "RUPEE" in s:
            return "INR"
        if "$" in s or "USD" in s:
            return "USD"
        if "€" in s or "EUR" in s:
            return "EUR"
        if "£" in s or "GBP" in s:
            return "GBP"
        # Standard 3 letter currency code or INR
        match = re.search(r"[A-Z]{3}", s)
        return match.group(0) if match else "INR"

    @field_validator("subtotal", "tax", mode="before")
    @classmethod
    def validate_nullable_float(cls, v):
        return clean_numeric(v)

    @field_validator("total", mode="before")
    @classmethod
    def validate_total(cls, v):
        val = clean_numeric(v)
        return val if val is not None else 0.0

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v):
        val = clean_numeric(v)
        if val is None:
            return 0.80
        if val > 1.0:
            val = val / 100.0  # Handle 0-100 scale gracefully
        return max(0.0, min(1.0, val))

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        if not v:
            return "Other"
        target = str(v).strip().title()
        for cat in ALLOWED_CATEGORIES:
            if cat.lower() == target.lower():
                return cat
        # Common heuristics
        low = target.lower()
        if any(w in low for w in ("cafe", "coffee", "restaurant", "dining", "meal", "food", "grocery")):
            return "Food"
        if any(w in low for w in ("taxi", "uber", "flight", "fuel", "petrol", "hotel", "travel")):
            return "Travel"
        if any(w in low for w in ("cloud", "saas", "software", "license", "subscription", "hosting")):
            return "Software"
        if any(w in low for w in ("hardware", "laptop", "monitor", "cable", "equipment")):
            return "Equipment"
        if any(w in low for w in ("electric", "power", "internet", "wifi", "bill", "water", "utility")):
            return "Utilities"
        return "Other"

    @model_validator(mode="after")
    def compute_math_and_defaults(self):
        # If total is 0 but subtotal exists and tax exists, calculate total
        if self.total == 0.0:
            if self.subtotal is not None and self.subtotal > 0:
                self.total = round(self.subtotal + (self.tax or 0.0), 2)
            elif self.line_items:
                calc = sum(item.qty * item.price for item in self.line_items)
                if calc > 0:
                    self.total = round(calc + (self.tax or 0.0), 2)
        return self

class ReceiptUpdate(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None
    category: Optional[str] = None
    line_items: Optional[List[LineItem]] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class ReceiptRecord(BaseModel):
    id: str
    filename: str
    image_path: str
    status: str  # queued, scanning, done, needs review, error
    created_at: str
    date: Optional[str] = None
    vendor: str = "Unknown Vendor"
    currency: str = "INR"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float = 0.0
    payment_method: Optional[str] = None
    category: str = "Other"
    line_items: List[LineItem] = Field(default_factory=list)
    confidence: float = 0.85
    notes: Optional[str] = None
    raw_model_output: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    is_synthetic: bool = False

    class Config:
        from_attributes = True
