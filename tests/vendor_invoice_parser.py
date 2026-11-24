"""Read a vendor invoice PDF (text-based) into the data needed to build a PO.

The extraction is heuristic: it looks for common Vietnamese/English labels and a
line-item table whose header contains recognisable column names. Invoices with
a different layout may need the label/keyword lists below adjusted.

Requires ``pdfplumber`` (``pip install -e ".[pdf]"``), imported lazily so the
pure helpers (``parse_number`` ...) work without it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

VENDOR_LABELS = (
    r"nhà cung cấp",
    r"đơn vị bán(?: hàng)?",
    r"tên đơn vị bán",
    r"người bán",
    r"seller",
    r"supplier",
    r"vendor",
    r"from",
)
INVOICE_NO_LABELS = (r"số hóa đơn", r"số hđ", r"invoice\s*(?:no\.?|number|#)", r"số")
SUBTOTAL_LABELS = (r"cộng tiền hàng", r"tạm tính", r"thành tiền chưa thuế", r"subtotal")
TOTAL_LABELS = (r"tổng cộng", r"tổng tiền thanh toán", r"tổng thanh toán", r"total")

COLUMN_KEYWORDS = {
    "name": ("tên hàng", "tên sản phẩm", "diễn giải", "mô tả", "description", "product", "item"),
    "qty": ("số lượng", "sl", "qty", "quantity"),
    "price": ("đơn giá", "unit price", "price", "giá"),
    "amount": ("thành tiền", "amount"),
    "tax": ("thuế suất", "vat rate", "tax rate", "% thuế"),
}
VAT_RATE_LABELS = (r"thuế suất[^:\n]*", r"vat rate[^:\n]*", r"tax rate[^:\n]*")


@dataclass
class InvoiceLine:
    name: str
    qty: float
    price: float
    amount: float | None = None  # "Thành tiền" of the line, if the table has that column
    tax_rate: float | None = None  # VAT % of the line, if the table has a tax-rate column


@dataclass
class VendorInvoice:
    source: str
    vendor: str
    lines: list[InvoiceLine] = field(default_factory=list)
    invoice_no: str | None = None
    vat_rate: float | None = None  # invoice-level VAT %, used when lines carry no rate
    subtotal: float | None = None
    total: float | None = None
    invoice_date: date | None = None  # "Ngày 12 tháng 10 năm 2026"
    serial: str | None = None  # "Ký hiệu (Serial): 1C26TTD"


def _invoice_date(lines: list[str]) -> date | None:
    """'Ngày (date) 12 tháng (month) 10 năm (year) 2026' or 'Ngày: 12/10/2026'."""
    text = "\n".join(lines)
    m = re.search(
        r"ngày\b[^\d\n]*(\d{1,2})\s*tháng[^\d\n]*(\d{1,2})\s*năm[^\d\n]*(\d{4})", text, re.IGNORECASE
    )
    if not m:
        m = re.search(r"ngày[^\d\n]*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", text, re.IGNORECASE)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _serial(lines: list[str]) -> str | None:
    for line in lines:
        m = re.search(r"ký hiệu\s*(?:\([^)]*\))?\s*[:：]\s*(\S+)", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def parse_number(text: str) -> float:
    """Parse '1.234.567,89', '1,234,567.89', '1 234', '100000' into a float."""
    s = re.sub(r"[^\d.,-]", "", text.strip())
    if not s or s in {"-", ".", ","}:
        raise ValueError(f"Not a number: {text!r}")
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        # The separator that appears last is the decimal one.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma or has_dot:
        sep = "," if has_comma else "."
        parts = s.split(sep)
        # '1.234' / '1,234,567' (groups of exactly 3 digits) are thousands separators.
        if len(parts) > 2 or (len(parts[-1]) == 3 and len(parts[0]) <= 3):
            s = s.replace(sep, "")
        else:
            s = s.replace(sep, ".")
    return float(s)


def _first_match(lines: list[str], labels: tuple[str, ...]) -> str | None:
    """Value after 'label: value' (same line) or the next non-empty line."""
    for pattern in labels:
        rx = re.compile(rf"^\s*(?:{pattern})\s*(?:\([^)]*\))?\s*[:：]\s*(.*)$", re.IGNORECASE)
        for i, line in enumerate(lines):
            m = rx.match(line)
            if not m:
                continue
            value = m.group(1).strip()
            if value:
                return value
            for nxt in lines[i + 1 : i + 3]:
                if nxt.strip():
                    return nxt.strip()
    return None


def _amount_after(lines: list[str], labels: tuple[str, ...]) -> float | None:
    for pattern in labels:
        rx = re.compile(rf"(?:{pattern})[^\d\n]*([\d][\d.,\s]*)", re.IGNORECASE)
        for line in lines:
            m = rx.search(line)
            if m:
                try:
                    return parse_number(m.group(1))
                except ValueError:
                    continue
    return None


def _percent(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
    return parse_number(m.group(1)) if m else None


def _vat_rate(lines: list[str]) -> float | None:
    for pattern in VAT_RATE_LABELS:
        rx = re.compile(rf"{pattern}[:：]\s*(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
        for line in lines:
            m = rx.search(line)
            if m:
                return parse_number(m.group(1))
    return None


def _column_index(header: list[str], key: str) -> int | None:
    for idx, cell in enumerate(header):
        cell_l = cell.lower()
        if any(k in cell_l for k in COLUMN_KEYWORDS[key]):
            return idx
    return None


def _lines_from_tables(tables: list[list[list[str | None]]]) -> list[InvoiceLine]:
    result: list[InvoiceLine] = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [(c or "").replace("\n", " ").strip() for c in table[0]]
        name_i = _column_index(header, "name")
        qty_i = _column_index(header, "qty")
        price_i = _column_index(header, "price")
        amount_i = _column_index(header, "amount")
        tax_i = _column_index(header, "tax")
        if name_i is None or qty_i is None or price_i is None:
            continue
        for row in table[1:]:
            cells = [(c or "").replace("\n", " ").strip() for c in row]
            if max(name_i, qty_i, price_i) >= len(cells) or not cells[name_i]:
                continue
            if not re.search(r"[^\W\d_]", cells[name_i]):
                continue  # column-number row "(1) (2) ..." or a stray number
            try:
                qty, price = parse_number(cells[qty_i]), parse_number(cells[price_i])
            except ValueError:
                continue  # total rows, blank rows, notes
            amount = None
            if amount_i is not None and amount_i < len(cells):
                try:
                    amount = parse_number(cells[amount_i])
                except ValueError:
                    pass
            tax_rate = _percent(cells[tax_i]) if tax_i is not None and tax_i < len(cells) else None
            result.append(InvoiceLine(cells[name_i], qty, price, amount, tax_rate))
    return result


def parse_vendor_invoice(path: str | Path) -> VendorInvoice:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('pdfplumber is required: pip install -e ".[pdf]"') from exc

    path = Path(path)
    text_lines: list[str] = []
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_lines.extend((page.extract_text() or "").splitlines())
            tables.extend(page.extract_tables())

    non_empty = [ln for ln in text_lines if ln.strip()]
    vendor = _first_match(non_empty, VENDOR_LABELS) or (non_empty[0].strip() if non_empty else "")
    return VendorInvoice(
        source=path.name,
        vendor=vendor,
        lines=_lines_from_tables(tables),
        invoice_no=_first_match(non_empty, INVOICE_NO_LABELS),
        vat_rate=_vat_rate(non_empty),
        subtotal=_amount_after(non_empty, SUBTOTAL_LABELS),
        total=_amount_after(non_empty, TOTAL_LABELS),
        invoice_date=_invoice_date(non_empty),
        serial=_serial(non_empty),
    )
