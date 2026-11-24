"""Create RFQ -> confirm -> Purchase Order from vendor invoice PDFs.

Invoice PDFs are taken from, in order: ``--invoice <file|folder>`` (repeatable),
``$VENDOR_INVOICE_PATH``, an interactive prompt on the terminal, then the folder
``tests/data/vendor_invoices``. Each PDF is read for its vendor and product lines,
then the RFQ is built in the Odoo UI and confirmed into a PO.

Prerequisites: a live Odoo 17 (see CLAUDE.md for ODOO_* variables), ``pdfplumber``
installed, and the vendor and products from the invoice already existing in Odoo.
The test never creates master data: a missing vendor/product fails the test.
It leaves the created PO in the database (use a test DB).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

from odoo_playwright.ui_async import AsyncOdooUI

from .vendor_invoice_parser import VendorInvoice, parse_number, parse_vendor_invoice

DEFAULT_INVOICE_DIR = Path(__file__).parent / "data" / "vendor_invoices"

# Odoo 17 many2one autocomplete items (older markup kept as fallback).
AUTOCOMPLETE_ITEM = ".o-autocomplete--dropdown-item, .ui-autocomplete li"
TOLERANCE = 0.01

# Save button markup differs between Odoo builds/themes; tried in order.
SAVE_BUTTON_SELECTORS = (
    # CC1 renders it as <span role="button" class="o_form_button_save">Lưu</span>.
    ".o_form_button_save",
    ".o_form_status_indicator button[data-hotkey='s']",
    ".o_control_panel button[data-hotkey='s']",
    ".o_control_panel button:has(.fa-cloud-upload)",
    ".o_control_panel button[title*='Lưu']",
    ".o_control_panel button[title*='Save']",
    ".o_control_panel button:text-is('Lưu')",
    ".o_control_panel button:text-is('Save')",
)


async def _wait_dropdown_loaded(page, timeout: int = 10000) -> None:
    """Odoo first shows a 'Loading...' / 'Đang tải...' item; wait for the real results."""
    try:
        await page.wait_for_function(
            """(sel) => {
                const items = [...document.querySelectorAll(sel)].filter(e => e.offsetParent !== null);
                return items.length > 0 && !items.some(e => /^(đang tải|loading)/i.test(e.innerText.trim()));
            }""",
            arg=AUTOCOMPLETE_ITEM,
            timeout=timeout,
        )
    except Exception:
        pass  # the caller reports what the dropdown offered


# --------------------------------------------------------------------------
# Pure helper tests: no Odoo needed.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("100000", 100000.0),
        ("1.234.567", 1234567.0),
        ("1,234,567", 1234567.0),
        ("1.234.567,89", 1234567.89),
        ("1,234,567.89", 1234567.89),
        ("12,5", 12.5),
        ("2.5", 2.5),
        ("1 500 000 đ", 1500000.0),
    ],
)
def test_parse_number(text: str, expected: float) -> None:
    assert parse_number(text) == pytest.approx(expected)


def test_parse_number_rejects_text() -> None:
    with pytest.raises(ValueError):
        parse_number("Tổng cộng")


@pytest.mark.parametrize(
    ("product_type", "category", "group"),
    [
        ("product", "All / Vật tư xây dựng / Vật liệu san lấp và vật liệu đắp", "KDVT"),
        ("service", "All / Dịch vụ / Dịch vụ thi công", "Xây Lắp"),
        ("service", "All / Dịch vụ / BOQ", "HHDV - Dịch Vụ"),
        ("product", "All / Thiết bị / Thiết bị công trình / Hệ thống điện", "TSCĐ"),
        ("consu", "All / Công cụ dụng cụ / Bảo hộ lao động", "TSCĐ"),
        ("consu", "All / Văn phòng phẩm / Giấy các loại", "Khác"),
        ("product", "All / Saleable", "KDVT"),
    ],
)
def test_tax_group_for(product_type: str, category: str, group: str) -> None:
    assert tax_group_for(product_type, category) == group


# --------------------------------------------------------------------------
# Where the invoice PDFs come from
# --------------------------------------------------------------------------
def resolve_pdfs(raw: str) -> list[Path]:
    """Turn 'a.pdf; C:\\folder; "b.pdf"' into a list of existing PDF files.

    Entries are separated by ';' (or new lines). Surrounding quotes, as added by
    Windows "Copy as path" or drag-and-drop, are removed. A folder expands to its *.pdf.
    """
    pdfs: list[Path] = []
    for part in re.split(r"[;\n]", raw):
        part = part.strip().strip("\"'")
        if not part:
            continue
        path = Path(part).expanduser()
        if path.is_dir():
            found = sorted(path.glob("*.pdf"))
            if not found:
                raise ValueError(f"No .pdf files in folder: {path}")
            pdfs.extend(found)
        elif path.is_file() and path.suffix.lower() == ".pdf":
            pdfs.append(path)
        else:
            raise ValueError(f"Not an existing .pdf file or folder: {path}")
    return pdfs


def _ask_for_pdfs(request) -> list[Path]:
    """Prompt on the real terminal, even though pytest captures stdin/stdout."""
    capman = request.config.pluginmanager.getplugin("capturemanager")
    capman.suspend_global_capture(in_=True)
    try:
        if not sys.stdin.isatty():
            return []
        print("\nVendor invoice PDF(s) to turn into purchase orders.")
        print("Enter a file path, several paths separated by ';', or a folder. Empty line = cancel.")
        while True:
            raw = input("Invoice path: ")
            if not raw.strip():
                return []
            try:
                return resolve_pdfs(raw)
            except ValueError as exc:
                print(f"  {exc}. Try again.")
    finally:
        capman.resume_global_capture()


@pytest.fixture
def invoice_pdfs(request) -> list[Path]:
    """Invoice PDFs, by priority: --invoice, $VENDOR_INVOICE_PATH, prompt, default folder."""
    raw = ";".join(request.config.getoption("--invoice")) or os.getenv("VENDOR_INVOICE_PATH", "")
    if raw:
        try:
            pdfs = resolve_pdfs(raw)
        except ValueError as exc:
            pytest.fail(str(exc))
    else:
        pdfs = _ask_for_pdfs(request)
        if not pdfs and DEFAULT_INVOICE_DIR.is_dir():
            pdfs = sorted(DEFAULT_INVOICE_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip('No invoice given: use --invoice "<file or folder>" or run in a terminal to be asked')
    return pdfs


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------
async def _pick_autocomplete(ui: AsyncOdooUI, input_locator, text: str, what: str) -> str:
    """Type ``text`` in a many2one input and choose the best match from the dropdown."""
    await input_locator.click()
    await input_locator.fill(text)
    items = ui.page.locator(AUTOCOMPLETE_ITEM)
    try:
        await items.first.wait_for(state="visible", timeout=5000)
    except Exception:
        pytest.fail(f"{what} {text!r}: no match in Odoo (create it first)")
    await _wait_dropdown_loaded(ui.page)
    # Clicking the field first shows the unfiltered list; wait for the search results.
    try:
        await ui.page.wait_for_function(
            """([sel, q]) => [...document.querySelectorAll(sel)]
                .filter(e => e.offsetParent !== null)
                .some(e => e.innerText.replace(/\\s+/g, ' ').toLowerCase().includes(q))""",
            arg=[AUTOCOMPLETE_ITEM, " ".join(text.split()).lower()],
            timeout=10000,
        )
    except Exception:
        pass  # reported below with what the dropdown offered

    texts = [" ".join(t.split()) for t in await items.all_inner_texts()]
    wanted = " ".join(text.split()).lower()
    # Only an exact name ("Name" or "[CODE] Name"): a wrong product is worse than a failure.
    for idx, t in enumerate(texts):
        if t.lower() == wanted or t.lower().endswith(f"] {wanted}"):
            print(f"  {what}: {t!r}")
            await items.nth(idx).click()
            return t
    pytest.fail(f"{what} {text!r}: no record with exactly this name. Dropdown offered: {texts}")


async def _debug_dump(ui: AsyncOdooUI, tag: str) -> str:
    """Screenshot + visible buttons, so a failure shows what the page really looked like."""
    page = ui.page
    Path("screenshots").mkdir(exist_ok=True)
    shot = Path("screenshots") / f"{tag}.png"
    await page.screenshot(path=str(shot), full_page=True)
    buttons = await page.evaluate(
        """() => [...document.querySelectorAll('button')]
            .filter(b => b.offsetParent !== null)
            .map(b => `${b.innerText.trim() || b.title || b.name} [${b.className}]`)
            .slice(0, 25)"""
    )
    extra = await page.evaluate(
        """() => ({
            dialogs: [...document.querySelectorAll('.modal.show, .o_dialog')]
                .map(d => d.innerText.trim().slice(0, 600)),
            notes: [...document.querySelectorAll('.o_notification')]
                .map(n => n.innerText.trim().slice(0, 300)),
            status: [...document.querySelectorAll('.o_statusbar_buttons button')]
                .map(b => `${b.innerText.trim()} | name=${b.getAttribute('name')} | `
                    + `${b.offsetParent === null ? 'hidden' : 'visible'}`),
        })"""
    )
    return (
        f"url={page.url}\nscreenshot={shot}\n"
        f"dialogs: {extra['dialogs']}\nnotifications: {extra['notes']}\n"
        "statusbar buttons:\n  " + "\n  ".join(extra["status"])
        + "\nvisible buttons:\n  " + "\n  ".join(buttons)
    )


async def _open_new_rfq_form(ui: AsyncOdooUI, pdf_path: Path) -> None:
    """Click New on the RFQ list and wait for the form; no silent fallbacks."""
    page = ui.page
    new_btn = page.locator(
        "button.o_list_button_add, button.o_form_button_create, "
        "button[name='create'], button[data-hotkey='c']"
    ).locator("visible=true").first
    try:
        await new_btn.wait_for(state="visible", timeout=15000)
        await new_btn.click()
        await page.locator(".o_form_view").wait_for(state="visible", timeout=15000)
    except Exception as exc:
        info = await _debug_dump(ui, f"rfq_new_{pdf_path.stem}")
        pytest.fail(f"Could not open a new RFQ form: {exc}\n{info}")


async def _shot(ui: AsyncOdooUI, name: str) -> None:
    """Progress screenshot (screenshots/step_<name>.png) to see where a run gets stuck."""
    Path("screenshots").mkdir(exist_ok=True)
    await ui.page.screenshot(path=str(Path("screenshots") / f"step_{name}.png"), full_page=True)


async def _save_rfq(ui: AsyncOdooUI) -> None:
    """Click the Save button (several known markups), else Alt+S; verify the record got an id."""
    page = ui.page
    clicked = None
    for selector in SAVE_BUTTON_SELECTORS:
        btn = page.locator(selector).locator("visible=true").first
        try:
            await btn.wait_for(state="visible", timeout=3000)
            await btn.click()
            clicked = selector
            break
        except Exception:
            continue

    if clicked:
        print(f"  save: clicked the Save button ({clicked})")
    else:
        buttons = await page.evaluate(
            """() => [...document.querySelectorAll('.o_control_panel button, .o_form_status_indicator button')]
                .map(b => `${b.offsetParent === null ? '(hidden) ' : ''}`
                    + `${(b.innerText || '').trim()} | title=${b.title} | class=${b.className}`)"""
        )
        print("  save: Save button NOT found, using Alt+S. Control panel buttons:")
        for line in buttons:
            print(f"    {line}")
        await page.keyboard.press("Alt+s")
    await ui.wait.for_all()

    # Odoo refuses to save while a required field is empty and marks it invalid.
    invalid = page.locator(".o_form_view .o_field_invalid")
    if await invalid.count():
        names = [await invalid.nth(i).get_attribute("name") for i in range(await invalid.count())]
        await _shot(ui, "3_save_refused")
        pytest.fail(f"Odoo rejected the save: required fields still empty: {names}")

    # A new record gets an id in the URL once it is really saved.
    try:
        await page.wait_for_function(
            "() => /[#&?]id=\\d+/.test(window.location.href)", timeout=10000
        )
    except Exception:
        await _shot(ui, "3_not_saved")
        pytest.fail(f"The RFQ was not saved (no record id in the URL): {page.url}")


async def _close_dropdowns(ui: AsyncOdooUI) -> None:
    """Close any open many2one dropdown/popover, otherwise the next click only closes it."""
    page = ui.page
    open_menus = page.locator(f"{AUTOCOMPLETE_ITEM}, .o_popover").locator("visible=true")
    for _ in range(3):
        if await open_menus.count() == 0:
            break
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
    # Move focus out of the field so focusing does not reopen the autocomplete.
    active = page.locator(".o_form_sheet .oe_title, .o_form_sheet h1").first
    # A modal (e.g. Odoo's error dialog) blocks the click; leave it for the caller.
    if await active.count() and not await page.locator(".modal.show").count():
        await active.click()
    await ui.wait.for_ajax()


async def _lines_subtotal(ui: AsyncOdooUI) -> float:
    """Sum of the line subtotals shown in the order lines (language independent)."""
    cells = ui.page.locator(
        ".o_field_widget[name='order_line'] .o_data_row td[name='price_subtotal']"
    )
    await cells.first.wait_for(state="visible", timeout=10000)
    return sum(parse_number(t) for t in await cells.all_inner_texts())


async def _pick_first_option(ui: AsyncOdooUI, input_locator, what: str) -> None:
    """Open a many2one dropdown without typing and choose its first real record.

    The dropdown sometimes closes between reading it and clicking (re-render after
    an onchange), so a failed click reopens it once before giving up.
    """
    for attempt in (1, 2):
        try:
            await _try_pick_first_option(ui, input_locator, what)
            return
        except Exception as exc:
            if attempt == 2:
                print(f"  required {what}: could not pick a value ({type(exc).__name__}), left empty")
                await ui.page.keyboard.press("Escape")
                return
            print(f"  required {what}: dropdown closed before the click, reopening")


async def _try_pick_first_option(ui: AsyncOdooUI, input_locator, what: str) -> bool:
    items = ui.page.locator(AUTOCOMPLETE_ITEM).locator("visible=true")
    widget = input_locator.locator("xpath=ancestor::div[contains(@class,'o_field_widget')][1]")
    opened = False
    # Try: focus, the arrow key, then the dropdown caret button.
    for attempt in ("click", "arrow", "caret"):
        if attempt == "click":
            await input_locator.click()
        elif attempt == "arrow":
            await input_locator.press("ArrowDown")
        else:
            caret = widget.locator(".o_dropdown_button")
            if await caret.count() == 0:
                break
            await caret.first.click()
        try:
            await items.first.wait_for(state="visible", timeout=3000)
            await _wait_dropdown_loaded(ui.page)
            opened = True
            break
        except Exception:
            continue
    if not opened:
        print(f"  required {what}: dropdown has no suggestions, left empty")
        return False
    texts = [" ".join(t.split()) for t in await items.all_inner_texts()]
    skip = ("search", "create", "start typing", "tìm", "tạo", "đang tải", "loading")
    for idx, t in enumerate(texts):
        if t and not t.lower().startswith(skip):
            await items.nth(idx).click(timeout=5000)
            await ui.wait.for_ajax()
            print(f"  required {what}: picked first option {t!r}")
            return True
    # Some fields (CC1's journal_id) offer only "Search More...": take the first row there.
    search_more = [i for i, t in enumerate(texts) if t.lower().startswith(("search more", "tìm kiếm thêm"))]
    if search_more:
        await items.nth(search_more[0]).click(timeout=5000)
        dialog = ui.page.locator(".modal.show").last
        first_row = dialog.locator(".o_data_row").first
        try:
            await first_row.wait_for(state="visible", timeout=10000)
        except Exception:
            await ui.page.keyboard.press("Escape")
            print(f"  required {what}: 'Search More' dialog has no records, left empty")
            return False
        label = " | ".join((await first_row.inner_text()).split("\t")).strip()
        await first_row.locator("td.o_data_cell").first.click()
        await dialog.wait_for(state="hidden", timeout=10000)
        await ui.wait.for_ajax()
        print(f"  required {what}: picked first row of 'Search More': {label!r}")
        return True
    print(f"  required {what}: only create/search entries offered ({texts}), left empty")
    return False


async def _fill_required_defaults(ui: AsyncOdooUI, scope_selector: str) -> None:
    """Every empty required many2one / selection field in scope gets its first value."""
    widgets = ui.page.locator(scope_selector)
    for i in range(await widgets.count()):
        widget = widgets.nth(i)
        name = await widget.get_attribute("name") or f"#{i}"
        field = widget.locator("input, select, textarea").first
        if await field.count() == 0 or not await field.is_visible():
            continue
        tag = await field.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            current = await field.evaluate("e => e.value")
            if current in ("", "false"):
                values = await field.evaluate("e => [...e.options].map(o => o.value)")
                first = next((v for v in values if v not in ("", "false")), None)
                if first is not None:
                    await field.select_option(value=first)
                    print(f"  required {name}: selected first option")
            continue
        if await field.get_attribute("type") in ("checkbox", "radio"):
            continue
        if await field.input_value():
            continue
        classes = await widget.get_attribute("class") or ""
        if "many2one" in classes:
            await _pick_first_option(ui, field, name)
        else:
            print(f"  required {name}: empty but not a many2one/selection, left empty")


async def _decimal_point(page) -> str:
    """Decimal separator of the Odoo user's language ('.' for English, ',' for Vietnamese)."""
    forced = os.getenv("ODOO_DECIMAL_POINT")
    if forced:
        return forced
    try:
        # Ask Odoo itself: the logged-in user's language and that language's decimal point.
        found = await page.evaluate(
            """async () => {
                const rpc = async (url, params) => {
                    const res = await fetch(url, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({jsonrpc: '2.0', method: 'call', params}),
                    });
                    return (await res.json()).result;
                };
                const info = await rpc('/web/session/get_session_info', {});
                const lang = info.user_context.lang;
                const rows = await rpc('/web/dataset/call_kw/res.lang/search_read', {
                    model: 'res.lang', method: 'search_read',
                    args: [[['code', '=', lang]], ['decimal_point']], kwargs: {},
                });
                return rows[0].decimal_point;
            }"""
        )
        if found:
            return found
    except Exception:
        pass
    try:
        return await page.evaluate(
            """() => {
                const lang = document.documentElement.lang || navigator.language || 'en-US';
                return new Intl.NumberFormat(lang).formatToParts(1.1)
                    .find(p => p.type === 'decimal').value;
            }"""
        )
    except Exception:
        return "."


def _typed_number(value: float, decimal_point: str) -> str:
    """Plain number as typed into an Odoo field: no thousands separator, locale decimal point."""
    text = format(value, "f").rstrip("0").rstrip(".")
    return text.replace(".", decimal_point)


_RPC_JS = """async ([model, method, args, kwargs]) => {
    const res = await fetch(`/web/dataset/call_kw/${model}/${method}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {model, method, args, kwargs}}),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error.data ? data.error.data.message : data.error.message);
    return data.result;
}"""


async def _rpc(page, model: str, method: str, args: list, **kwargs):
    """JSON-RPC call as the logged-in user (lookups behind the test's choices)."""
    return await page.evaluate(_RPC_JS, [model, method, args, kwargs])


# Which VAT group ("GTGT <group> <rate>% - IN") fits a product, checked top to bottom.
# Each rule: (product types it applies to, or None for all; keywords in the category path;
# group). CC1 purchase VAT groups: TSCĐ, HHDV - Dịch Vụ, KDVT, Xây Lắp, Đầu tư, Nhập khẩu, Khác.
TAX_GROUP_RULES: tuple[tuple[tuple[str, ...] | None, tuple[str, ...], str], ...] = (
    (("service",), ("thi công", "xây lắp", "nhân công"), "Xây Lắp"),
    (("service",), (), "HHDV - Dịch Vụ"),
    (None, ("thiết bị", "công cụ dụng cụ", "ccdc", "tscđ", "tài sản"), "TSCĐ"),
    (None, ("expenses", "văn phòng phẩm", "chi phí"), "Khác"),
    (None, ("vật tư", "vật liệu", "hàng hóa", "hàng hoá", "nông sản", "nguyên vật liệu"), "KDVT"),
    (None, (), "KDVT"),  # any other stockable/consumable goods
)


def tax_group_for(product_type: str, category_path: str) -> str:
    """VAT group for a product type (service/product/consu) and its category path."""
    path = category_path.lower()
    for types, keywords, group in TAX_GROUP_RULES:
        if types is not None and product_type not in types:
            continue
        if not keywords or any(k in path for k in keywords):
            return group
    return "Khác"


async def _purchase_tax_for(page, product_label: str, rate: float) -> tuple[str | None, str]:
    """(tax name, reason) of the purchase tax to use for this product at ``rate`` %.

    1. the product's own default purchase tax, if it has that rate;
    2. otherwise the VAT group chosen from the product type and category (TAX_GROUP_RULES).
    """
    m = re.match(r"\[([^\]]+)\]\s*(.*)", product_label)
    domain = [["default_code", "=", m.group(1)]] if m else [["name", "=", product_label]]
    products = await _rpc(page, "product.product", "search_read", [domain],
                          fields=["detailed_type", "categ_id", "supplier_taxes_id"], limit=1)
    if not products:
        return None, f"product {product_label!r} not readable"
    product = products[0]
    info = await page.evaluate(
        """async () => (await (await fetch('/web/session/get_session_info', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
        })).json()).result"""
    )
    company = (info.get("user_companies") or {}).get("current_company")
    base = [["type_tax_use", "=", "purchase"], ["amount", "=", rate]]
    if company:
        base.append(["company_id", "=", company])
    if product["supplier_taxes_id"]:
        own = await _rpc(page, "account.tax", "search_read",
                         [base + [["id", "in", product["supplier_taxes_id"]]]],
                         fields=["name"], limit=1)
        if own:
            return own[0]["name"], "product's default purchase tax"
    category = await _rpc(page, "product.category", "read", [[product["categ_id"][0]]],
                          fields=["complete_name"])
    path = category[0]["complete_name"] if category else ""
    group = tax_group_for(product["detailed_type"], path)
    found = await _rpc(page, "account.tax", "search_read",
                       [base + [["name", "ilike", f"GTGT {group} "], ["name", "ilike", "- IN"]]],
                       fields=["name"], limit=1)
    reason = f"group {group!r} from type {product['detailed_type']!r}, category {path!r}"
    return (found[0]["name"] if found else None), reason


async def _set_tax(ui: AsyncOdooUI, rate: float, product_label: str | None = None) -> None:
    """Replace the taxes of the line being edited with the purchase tax of ``rate`` %.

    With ``product_label`` the VAT group is chosen per product (see TAX_GROUP_RULES);
    otherwise, or if that tax is not offered, the first purchase (IN) tax of the rate is used.
    """
    page = ui.page
    wanted_name = None
    if product_label:
        wanted_name, reason = await _purchase_tax_for(page, product_label, rate)
        print(f"  tax {rate:g}%: wanted {wanted_name!r} ({reason})")
    cell = page.locator(".o_data_row.o_selected_row td[name='taxes_id']")
    if await cell.count() == 0:
        pytest.fail("No 'Taxes' column on the order lines: enable it in the optional-columns menu")

    # Product defaults may already put other taxes on the line; remove them first.
    for _ in range(10):
        delete = cell.locator(".o_tag .o_delete")
        if await delete.count() == 0:
            break
        await delete.first.click()
        await ui.wait.for_ajax()

    label = f"{rate:g}"
    token = re.compile(rf"(?<![\d.,]){re.escape(label)}\s*%")
    seen: list[str] = []
    if wanted_name:
        wanted_text = " ".join(wanted_name.split())
        field = cell.locator("input").first
        await field.click()
        await field.fill(wanted_name)
        items = page.locator(AUTOCOMPLETE_ITEM)
        try:
            await items.first.wait_for(state="visible", timeout=5000)
            await page.wait_for_function(
                r"""([sel, q]) => [...document.querySelectorAll(sel)].some(e =>
                    e.offsetParent !== null && e.innerText.replace(/\s+/g, ' ').trim() === q)""",
                arg=[AUTOCOMPLETE_ITEM, wanted_text],
                timeout=10000,
            )
        except Exception:
            pass
        texts = [" ".join(t.split()) for t in await items.all_inner_texts()]
        exact = [i for i, t in enumerate(texts) if t == wanted_text]
        if exact:
            await items.nth(exact[0]).click()
            await ui.wait.for_ajax()
            print(f"  tax {label}%: {texts[exact[0]]!r}")
            return
        print(f"  tax {label}%: {wanted_name!r} not offered ({texts}), using the first IN tax")
        await field.fill("")
    for query in (f"{label}%", label):
        field = cell.locator("input").first
        await field.click()
        await field.fill(query)
        items = page.locator(AUTOCOMPLETE_ITEM)
        try:
            await items.first.wait_for(state="visible", timeout=5000)
        except Exception:
            continue
        await _wait_dropdown_loaded(page)
        texts = [" ".join(t.split()) for t in await items.all_inner_texts()]
        seen = texts
        candidates = [i for i, t in enumerate(texts) if token.search(t)]
        # Odoo marks input (purchase) taxes with IN and output (sales) taxes with OUT.
        purchase = [i for i in candidates if re.search(r"\bIN\b", texts[i]) and "OUT" not in texts[i]]
        unmarked = [i for i in candidates if not re.search(r"\b(IN|OUT)\b", texts[i])]
        chosen = purchase[0] if purchase else (unmarked[0] if unmarked else None)
        if chosen is not None:
            print(f"  tax {label}%: {texts[chosen]!r} (offered: {texts})")
            await items.nth(chosen).click()
            await ui.wait.for_ajax()
            return
        await field.fill("")
    pytest.fail(
        f"No purchase (IN) tax of {label}% found. Dropdown offered: {seen}"
    )


async def _fill_analytic(ui: AsyncOdooUI) -> None:
    """Fill the analytic distribution of the selected line: first account of every plan."""
    page = ui.page
    cell = page.locator(".o_data_row.o_selected_row td[name='analytic_distribution']")
    if await cell.count() == 0:
        print("  analytic: no 'Analytic Distribution' column on the lines, skipped")
        return
    if await cell.locator(".o_tag").count():
        print("  analytic: already set by default")
        return
    await cell.click()
    popup = page.locator(
        ".analytic_distribution_popup, .o_popover:has(input.o-autocomplete--input)"
    ).locator("visible=true").first
    try:
        await popup.wait_for(state="visible", timeout=5000)
    except Exception:
        print("  analytic: the distribution popup did not open, skipped")
        return
    # Odoo 17 popup: one table, one column per analytic plan ("Loại hình (100%)",
    # "Mã vụ việc (0%)", ...), and one row per split with an account input per plan
    # plus a percentage. Fill every empty plan column of the first row; the row's
    # percentage (100) then applies to all plans.
    data_row = popup.locator("tr:has(input.o-autocomplete--input)").first
    header = popup.locator("tr").first
    plans = [" ".join(t.split()) for t in await header.locator("td, th").all_inner_texts()]
    filled = 0
    for i in range(await data_row.locator("input.o-autocomplete--input").count()):
        field = popup.locator("tr:has(input.o-autocomplete--input)").first.locator(
            "input.o-autocomplete--input"
        ).nth(i)
        plan = plans[i] if i < len(plans) else f"plan {i + 1}"
        if await field.input_value():
            print(f"  analytic {plan}: already {await field.input_value()!r}")
            continue
        await _pick_first_option(ui, field, f"analytic {plan}")
        filled += 1
    pct = popup.locator("tr:has(input.o-autocomplete--input)").first.locator(
        "td.numeric_column_width input"
    ).first
    if await pct.count():
        current = (await pct.input_value()).strip()
        if parse_number(current or "0") < 100:
            await pct.click()
            await pct.press("Control+a")
            await pct.fill("100")
            await pct.press("Tab")
            await ui.wait.for_ajax()
            print(f"  analytic: percentage {current!r} -> 100")
    totals = [" ".join(t.split()) for t in await header.locator("td, th").all_inner_texts()]
    print(f"  analytic plans after filling: {[t for t in totals if '%' in t]}")
    # Clicking another cell of the same row closes the popup and keeps the row in edit mode.
    await page.locator(".o_data_row.o_selected_row td[name='product_qty']").click()
    await ui.wait.for_ajax()
    print(f"  analytic: filled {filled} account(s)")


async def _add_line(
    ui: AsyncOdooUI,
    index: int,
    product: str,
    qty: float,
    price: float,
    tax_rate: float | None = None,
) -> None:
    page = ui.page
    decimal_point = await _decimal_point(page)
    print(f"  line {index}: Odoo decimal point is {decimal_point!r}")
    await page.locator(".o_field_x2many_list_row_add a").first.click()
    row = page.locator(".o_data_row.o_selected_row")
    await row.wait_for(state="visible", timeout=10000)

    product_label = await _pick_autocomplete(
        ui, row.locator("td[name='product_id'] input").first, product, f"Product (line {index})"
    )
    await ui.wait.for_all()

    # Product selection may re-render the row; re-locate the cells afterwards.
    for name, value in (("product_qty", qty), ("price_unit", price)):
        cell = page.locator(f".o_data_row.o_selected_row td[name='{name}'] input").first
        await cell.click()
        await cell.press("Control+a")
        await cell.fill(_typed_number(value, decimal_point))
    await ui.wait.for_ajax()
    if tax_rate is not None:
        await _set_tax(ui, tax_rate, product_label)
    await _fill_analytic(ui)
    await _fill_required_defaults(
        ui, ".o_data_row.o_selected_row .o_field_widget.o_required_modifier"
    )


# --------------------------------------------------------------------------
# Main scenario
# --------------------------------------------------------------------------
@pytest.mark.integration
async def test_create_po_from_vendor_invoice(
    invoice_pdfs: list[Path], async_odoo_ui: AsyncOdooUI, odoo_config
) -> None:
    for pdf_path in invoice_pdfs:
        print(f"\n== {pdf_path.name}")
        try:
            await _create_po_from_invoice(async_odoo_ui, odoo_config, pdf_path)
        except Exception:
            print("\n--- page state at failure ---")
            print(await _debug_dump(async_odoo_ui, f"fail_{pdf_path.stem}"))
            raise


async def _create_po_from_invoice(ui: AsyncOdooUI, odoo_config, pdf_path: Path) -> None:
    page = ui.page

    invoice: VendorInvoice = parse_vendor_invoice(pdf_path)
    assert invoice.vendor, f"{pdf_path.name}: could not read the vendor name"
    assert invoice.lines, f"{pdf_path.name}: no product lines found (check the table header names)"
    for line in invoice.lines:
        if line.amount is not None:  # invoices round each line to whole đồng
            assert line.qty * line.price == pytest.approx(line.amount, abs=1), (
                f"{pdf_path.name}: {line.name!r}: {line.qty} x {line.price} "
                f"!= line amount {line.amount}"
            )
    expected_untaxed = sum(line.qty * line.price for line in invoice.lines)
    if invoice.subtotal is not None:
        assert expected_untaxed == pytest.approx(invoice.subtotal, abs=1), (
            f"{pdf_path.name}: parsed lines sum to {expected_untaxed}, "
            f"invoice subtotal says {invoice.subtotal}"
        )

    # 1. Open Purchase > Orders > Requests for Quotation and start a new RFQ.
    await page.goto(f"{odoo_config.base_url}/web#action=purchase.purchase_rfq&view_type=list")
    await ui.wait.for_all()
    await _open_new_rfq_form(ui, pdf_path)

    # 2. Vendor.
    # The vendor must be the one named on the invoice: no "first result" fallback.
    vendor_input = ui.get_field("partner_id")
    await vendor_input.click()
    await vendor_input.fill(invoice.vendor)
    items = page.locator(AUTOCOMPLETE_ITEM)
    try:
        await items.first.wait_for(state="visible", timeout=10000)
    except Exception:
        pytest.fail(f"Vendor {invoice.vendor!r} not found in Odoo (no suggestions)")
    await _wait_dropdown_loaded(page)
    def norm(s: str) -> str:
        # Odoo shows "Name ‒ <tax id>" in the dropdown: drop that suffix before comparing.
        s = re.sub(r"\s+[‒–—-]\s*[\d-]+\s*$", "", s)
        return re.sub(r"\s+", " ", s).strip().lower()

    offered = [" ".join(t.split()) for t in await items.all_inner_texts()]
    exact = [i for i, t in enumerate(offered) if norm(t) == norm(invoice.vendor)]
    if not exact:
        pytest.fail(
            f"Vendor {invoice.vendor!r} from the invoice does not exist in Odoo "
            f"(exact name). Odoo offered: {offered}"
        )
    await items.nth(exact[0]).click()
    print(f"  vendor: {offered[exact[0]]!r}")
    await ui.wait.for_all()
    await _shot(ui, "1_vendor")

    # Vendor Reference carries the supplier's invoice number for traceability.
    if invoice.invoice_no:
        ref = page.locator(".o_field_widget[name='partner_ref'] input").first
        if await ref.count() > 0:
            await ref.fill(invoice.invoice_no)

    # 3. Product lines.
    for i, line in enumerate(invoice.lines, start=1):
        rate = line.tax_rate if line.tax_rate is not None else invoice.vat_rate
        if rate is None:
            print(f"  line {i}: no VAT rate on the invoice, keeping Odoo's default taxes")
        await _add_line(ui, i, line.name, line.qty, line.price, rate)
        await _shot(ui, f"2_line{i}")

    # 4. Fill remaining required header fields with their first value, then save.
    # The line's analytic popup / dropdowns must be closed, or the first click is swallowed.
    await _close_dropdowns(ui)
    await _fill_required_defaults(
        ui, ".o_form_sheet .o_group .o_field_widget.o_required_modifier:not(.o_field_x2many)"
    )
    await _save_rfq(ui)
    await _shot(ui, "3_saved")
    rows = page.locator(".o_field_widget[name='order_line'] .o_data_row")
    assert await rows.count() == len(invoice.lines)
    assert await _lines_subtotal(ui) == pytest.approx(expected_untaxed, abs=1)
    if invoice.total is not None:
        form_text = await page.locator(".o_form_view").inner_text()
        numbers = []
        for raw in re.findall(r"\d[\d.,]*", form_text):
            try:
                numbers.append(parse_number(raw))
            except ValueError:
                pass
        assert any(abs(n - invoice.total) <= 1 for n in numbers), (
            f"{pdf_path.name}: invoice total {invoice.total} not found on the saved RFQ "
            "(taxes differ from the invoice?)"
        )

    # 5. Confirm Order -> Purchase Order.
    # An autocomplete left open (e.g. "Giao hàng đến") swallows the Confirm click.
    await _close_dropdowns(ui)
    await _shot(ui, "4_before_confirm")
    confirm = page.locator(".o_statusbar_buttons button[name='button_confirm']").locator(
        "visible=true"
    ).first
    left_draft = """() => {
        const b = document.querySelector('.o_statusbar_status button.o_arrow_button_current');
        return b && !['draft', 'sent'].includes(b.dataset.value);
    }"""
    dialog_or_done = """() => {
        if (document.querySelector('.modal.show, .o_dialog .modal')) return true;
        const b = document.querySelector('.o_statusbar_status button.o_arrow_button_current');
        return b && !['draft', 'sent'].includes(b.dataset.value);
    }"""
    for attempt in (1, 2):
        await confirm.wait_for(state="visible", timeout=10000)
        await confirm.click()
        await ui.wait.for_all()
        try:
            # Odoo's refusal dialog can come a beat after the RPC; wait for it or the new state.
            await page.wait_for_function(dialog_or_done, timeout=15000)
        except Exception:
            pass
        # Toasts disappear after a few seconds: capture them right after the click.
        notes = [" ".join(t.split()) for t in await page.locator(".o_notification").all_inner_texts()]
        dialogs = [
            " ".join(t.split())[:400] for t in await page.locator(".modal.show").all_inner_texts()
        ]
        print(f"  Confirm click {attempt}: notifications={notes} dialogs={dialogs}")
        if dialogs:
            await _shot(ui, "4_confirm_refused")
            pytest.fail(f"Odoo refused to confirm the RFQ: {dialogs}")
        if await page.evaluate(left_draft) or attempt == 2:
            break
        print("  still RFQ after Confirm: closing dropdowns and clicking once more")
        await _close_dropdowns(ui)
    await _shot(ui, "4_confirmed")
    # CC1 auto-locks confirmed orders: the current step is then "done" ("Đã khoá"),
    # rendered hidden (d-none), so only require it to be in the DOM.
    state = page.locator(".o_statusbar_status button.o_arrow_button_current").first
    await state.wait_for(state="attached", timeout=15000)
    current = await state.get_attribute("data-value")
    assert current in ("purchase", "done"), (
        f"Expected state 'purchase', got {current!r} "
        "('to approve' means the Double Validation threshold was exceeded)"
    )

    # Confirmed orders expose the Receipt smart button: the PO really went through.
    assert await page.locator(".oe_button_box [name='action_view_picking']").count() > 0
