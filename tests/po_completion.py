"""Finish a confirmed purchase order in the UI: receive the goods, bill, (optionally) pay.

Every step first checks the order's real state over JSON-RPC and skips what is already
done, so running it again on the same PO continues where the last run stopped instead
of creating a second receipt or bill. Steps:

1. confirm   draft/sent RFQ -> purchase (fills the missing analytic plans first)
2. receive   validate every receipt that is not done
3. bill      create the vendor bill from the PO (or reuse its draft bill), fill the
             vendor invoice data (number, serial, date) and post it
4. pay       optional: register the full payment of the posted bill

CC1 specifics handled here (see the memory notes): Vietnamese labels, so buttons are
found by ``name=``; Save is a <span class="o_form_button_save">; confirmed POs are
auto-locked ("done"); the bill needs description / ref / serial_no / tax_description.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from odoo_playwright.ui_async import AsyncOdooUI

_RPC_JS = """async ([model, method, args, kwargs]) => {
    const res = await fetch(`/web/dataset/call_kw/${model}/${method}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {model, method, args, kwargs}}),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error.data ? data.error.data.message : data.error.message);
    return data.result;
}"""


DIALOG = ".modal.show, .modal.d-block"


class StepError(AssertionError):
    """A completion step could not be done; the message says what Odoo showed."""


@dataclass
class BillData:
    """Vendor invoice data copied onto the bill."""

    ref: str  # invoice number ("Số"), e.g. 2955
    serial: str | None = None  # "Ký hiệu", e.g. 1C26TTD
    invoice_date: date | None = None
    description: str | None = None


@dataclass
class InvoicePart:
    """One vendor invoice inside a PO that groups several: its bill data and quantities."""

    data: BillData
    qty_by_po_line: dict[int, float]  # purchase.order.line id -> quantity on this invoice


async def rpc(ui: AsyncOdooUI, model: str, method: str, args: list, **kwargs):
    return await ui.page.evaluate(_RPC_JS, [model, method, args, kwargs])


async def shot(ui: AsyncOdooUI, name: str) -> None:
    """Best-effort screenshot: a failed screenshot must never hide the real result."""
    Path("screenshots").mkdir(exist_ok=True)
    try:
        await ui.page.screenshot(path=str(Path("screenshots") / f"complete_{name}.png"))
    except Exception as exc:
        print(f"  (screenshot {name} failed: {type(exc).__name__}: {exc})")


async def _settle(ui: AsyncOdooUI) -> None:
    await ui.wait.for_all()
    await ui.page.wait_for_timeout(500)


async def _close_dropdowns(ui: AsyncOdooUI) -> None:
    menus = ui.page.locator(".o-autocomplete--dropdown-item, .o_popover").locator("visible=true")
    for _ in range(3):
        if await menus.count() == 0:
            return
        await ui.page.keyboard.press("Escape")
        await ui.page.wait_for_timeout(300)


async def _dialog_texts(ui: AsyncOdooUI) -> list[str]:
    return [" ".join(t.split())[:500] for t in await ui.page.locator(DIALOG).all_inner_texts()]


async def _status(ui: AsyncOdooUI) -> str | None:
    """data-value of the current statusbar step (present even when hidden, e.g. 'done')."""
    current = ui.page.locator(".o_statusbar_status button.o_arrow_button_current").first
    try:
        await current.wait_for(state="attached", timeout=15000)
    except Exception:
        return None
    return await current.get_attribute("data-value")


async def _click_status_button(ui: AsyncOdooUI, name: str, what: str) -> None:
    await _close_dropdowns(ui)
    button = ui.page.locator(f".o_statusbar_buttons button[name='{name}']").locator("visible=true").first
    try:
        await button.wait_for(state="visible", timeout=10000)
    except Exception as exc:
        visible = await ui.page.evaluate(
            """() => [...document.querySelectorAll('.o_statusbar_buttons button')]
                .filter(b => b.offsetParent !== null).map(b => `${b.innerText.trim()} (${b.name})`)"""
        )
        raise StepError(f"{what}: button '{name}' not visible. Buttons: {visible}") from exc
    await button.click()
    await _settle(ui)


async def _accept_dialogs(ui: AsyncOdooUI, what: str, allowed: tuple[str, ...]) -> list[str]:
    """Click through confirmation dialogs whose text matches ``allowed``; fail on any other.

    Odoo errors (e.g. missing analytic, validation errors) must stop the run, while CC1's
    "date differs from the purchase" warnings only need a confirmation.
    """
    seen: list[str] = []
    for _ in range(4):
        await ui.page.wait_for_timeout(800)
        texts = await _dialog_texts(ui)
        if not texts:
            return seen
        text = texts[-1]
        seen.append(text)
        print(f"  {what}: dialog: {text[:300]}")
        if not any(re.search(p, text, re.IGNORECASE) for p in allowed):
            await shot(ui, f"{what}_dialog")
            raise StepError(f"{what}: Odoo showed: {text}")
        dialog = ui.page.locator(DIALOG).last
        primary = dialog.locator(".modal-footer .btn-primary").first
        if await primary.count() == 0:
            raise StepError(f"{what}: dialog without a confirm button: {text}")
        await primary.click()
        await _settle(ui)
    return seen


async def _wait_state(
    ui: AsyncOdooUI, model: str, record_id: int, field: str, wanted: tuple[str, ...],
    timeout_s: int = 120,
) -> str:
    """Poll ``field`` until it is in ``wanted`` or a dialog shows up (CC1 can be slow)."""
    value = ""
    for _ in range(timeout_s):
        value = (await rpc(ui, model, "read", [[record_id]], fields=[field]))[0][field]
        if value in wanted or await ui.page.locator(DIALOG).count():
            return value
        await ui.page.wait_for_timeout(1000)
    return value


async def _save(ui: AsyncOdooUI, what: str) -> None:
    await _close_dropdowns(ui)
    save = ui.page.locator(".o_form_button_save").locator("visible=true").first
    if await save.count():
        await save.click()
        await _settle(ui)
        # CC1 saves slowly: wait until the Save button goes away, a field turns invalid,
        # or Odoo shows a dialog / notification.
        try:
            await ui.page.wait_for_function(
                """() => {
                    const btn = document.querySelector('.o_form_button_save');
                    const saved = !btn || btn.offsetParent === null;
                    return saved || document.querySelector('.o_field_invalid, .o_invalid_cell, '
                        + '.modal.show, .modal.d-block, .o_notification.border-danger, .o_notification_bar.bg-danger');
                }""",
                timeout=90000,
            )
        except Exception:
            pass
    # A refused save keeps the Save button and marks fields (or list cells) invalid.
    invalid = ui.page.locator(".o_form_view .o_field_invalid, .o_form_view .o_invalid_cell")
    if await invalid.count() or await ui.page.locator(".o_form_button_save").locator("visible=true").count():
        names = [await invalid.nth(i).get_attribute("name") for i in range(await invalid.count())]
        notes = [" ".join(t.split()) for t in await ui.page.locator(".o_notification").all_inner_texts()]
        await shot(ui, f"{what}_invalid")
        raise StepError(f"{what}: Odoo refused to save, invalid fields: {names}, "
                        f"notifications: {notes}, dialogs: {await _dialog_texts(ui)}")
    dialogs = await _dialog_texts(ui)
    if dialogs:
        raise StepError(f"{what}: Odoo refused to save: {dialogs}")


async def _lang_format(ui: AsyncOdooUI) -> tuple[str, str]:
    """(date_format, decimal_point) of the logged-in user's language."""
    info = await ui.page.evaluate(
        """async () => (await (await fetch('/web/session/get_session_info', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
        })).json()).result.user_context.lang"""
    )
    rows = await rpc(ui, "res.lang", "search_read", [[["code", "=", info]]],
                     fields=["date_format", "decimal_point"])
    return (rows[0]["date_format"], rows[0]["decimal_point"]) if rows else ("%m/%d/%Y", ".")


async def _fill_input(ui: AsyncOdooUI, field: str, value: str, scope: str = ".o_form_view") -> bool:
    """Type into the visible input/textarea of field ``field``; False if the form has none."""
    widget = ui.page.locator(f"{scope} .o_field_widget[name='{field}']").locator("visible=true")
    if await widget.count() == 0:
        return False
    box = widget.first.locator("input, textarea").first
    if await box.count() == 0:
        return False
    await box.click()
    await box.press("Control+a")
    await box.fill(value)
    await box.press("Tab")
    await ui.wait.for_ajax()
    return True


async def _fill_in_any_tab(ui: AsyncOdooUI, field: str, value: str) -> bool:
    """Fill ``field`` wherever it is: Odoo 17 renders only the active notebook page, so
    open each tab until the field shows up. Leaves the first tab open again."""
    if await _fill_input(ui, field, value):
        return True
    tabs = ui.page.locator(".o_form_view .o_notebook .nav-link")
    found = False
    for i in range(await tabs.count()):
        await tabs.nth(i).click()
        await ui.page.wait_for_timeout(500)
        if await _fill_input(ui, field, value):
            found = True
            break
    if await tabs.count():
        await tabs.first.click()
    return found


async def open_record(ui: AsyncOdooUI, model: str, record_id: int) -> None:
    """Load the form of one record with a real page load (a hash change alone would keep the
    previous form on screen and let the next step act on it)."""
    await ui.page.goto("about:blank")
    await ui.page.goto(f"{ui.base_url}/web#model={model}&id={record_id}&view_type=form")
    # CC1's account.move form is slow: wait for the sheet and for Odoo's "Loading" to go.
    await ui.page.locator(".o_action_manager .o_form_view .o_form_sheet").first.wait_for(
        state="visible", timeout=120000
    )
    try:
        await ui.page.wait_for_function(
            """() => { const l = document.querySelector('.o_loading_indicator');
                       return !l || l.offsetParent === null; }""",
            timeout=120000,
        )
    except Exception:
        pass
    await _settle(ui)


async def find_po(ui: AsyncOdooUI, name_or_id: str | int) -> int:
    if isinstance(name_or_id, int) or str(name_or_id).isdigit():
        return int(name_or_id)
    rows = await rpc(ui, "purchase.order", "search_read", [[["name", "=", name_or_id]]],
                     fields=["id"], limit=2)
    if len(rows) != 1:
        raise StepError(f"Purchase order {name_or_id!r}: found {len(rows)} records")
    return rows[0]["id"]


async def po_info(ui: AsyncOdooUI, po_id: int) -> dict:
    return (await rpc(ui, "purchase.order", "read", [[po_id]], fields=[
        "name", "state", "partner_ref", "picking_ids", "invoice_ids", "invoice_status",
        "receipt_status", "order_line", "amount_total",
    ]))[0]


# --------------------------------------------------------------------------
# 1. confirm
# --------------------------------------------------------------------------
async def confirm(ui: AsyncOdooUI, po_id: int, fill_analytic: Callable[[AsyncOdooUI], Awaitable[None]]) -> None:
    info = await po_info(ui, po_id)
    if info["state"] not in ("draft", "sent"):
        print(f"  confirm: {info['name']} already {info['state']!r}, skipped")
        return
    await open_record(ui, "purchase.order", po_id)
    # Lines saved before all 4 mandatory plans were filled: complete them per line.
    rows = ui.page.locator(".o_field_widget[name='order_line'] .o_data_row")
    for i in range(await rows.count()):
        row = ui.page.locator(".o_field_widget[name='order_line'] .o_data_row").nth(i)
        await row.locator("td[name='product_qty']").click()
        await ui.page.locator(".o_data_row.o_selected_row").wait_for(state="visible", timeout=10000)
        await fill_analytic(ui)
    await _save(ui, "confirm")
    await _click_status_button(ui, "button_confirm", "confirm")
    state = ""
    for _ in range(3):
        state = await _wait_state(ui, "purchase.order", po_id, "state", ("purchase", "done", "to approve"))
        if state in ("purchase", "done"):
            break
        await _accept_dialogs(ui, "confirm", allowed=(r"khác ngày|different date|ngày.*khác",))
    if state not in ("purchase", "done"):
        raise StepError(f"confirm: {info['name']} is {state!r} after Confirm")
    print(f"  confirm: {info['name']} -> {state!r}")


# --------------------------------------------------------------------------
# 2. receive
# --------------------------------------------------------------------------
async def _backdate_receipt(ui: AsyncOdooUI, movement_date: date) -> None:
    """"Fill Actual Movement Date" (wizard fill.date.backdating) on the open receipt.

    CC1 refuses a bill dated before its receipts, so the receipt takes the vendor
    invoice's date instead of today.
    """
    # type="action" button: its name is the action id (2529 on CC1); the label may be translated.
    button = ui.page.locator(".o_statusbar_buttons button[name='2529']").locator("visible=true")
    if await button.count() == 0:
        button = ui.page.locator(".o_statusbar_buttons button").filter(
            has_text=re.compile("Fill Actual Movement Date|thực tế", re.I)
        ).locator("visible=true")
    if await button.count() == 0:
        raise StepError("receive: no 'Fill Actual Movement Date' button on the receipt")
    await button.first.click()
    wizard = ui.page.locator(DIALOG).last
    await wizard.wait_for(state="visible", timeout=15000)
    date_format, _ = await _lang_format(ui)
    box = wizard.locator(".o_field_widget[name='date_backdating'] input").first
    typed = movement_date.strftime(date_format) + " 08:00:00"
    await box.click()
    await box.press("Control+a")
    await box.fill(typed)
    await box.press("Enter")
    await ui.wait.for_ajax()
    await wizard.locator("button[name='fill_date_backdating']").first.click()
    await _settle(ui)
    print(f"  receive: actual movement date set to {typed}")


async def receive(ui: AsyncOdooUI, po_id: int, movement_date: date | None = None) -> None:
    info = await po_info(ui, po_id)
    pickings = await rpc(ui, "stock.picking", "read", [info["picking_ids"]],
                         fields=["name", "state", "picking_type_code"]) if info["picking_ids"] else []
    todo = [p for p in pickings if p["state"] not in ("done", "cancel") and p["picking_type_code"] == "incoming"]
    if not pickings:
        print(f"  receive: {info['name']} has no receipt (services only?), skipped")
        return
    if not todo:
        print(f"  receive: all receipts done ({[p['name'] for p in pickings]}), skipped")
        return
    for picking in todo:
        await open_record(ui, "stock.picking", picking["id"])
        if picking["state"] in ("draft", "confirmed", "waiting"):
            # Not reserved yet: "Check availability" first when Odoo offers it.
            check = ui.page.locator(".o_statusbar_buttons button[name='action_assign']").locator("visible=true")
            if await check.count():
                await check.first.click()
                await _settle(ui)
        if movement_date:
            await _backdate_receipt(ui, movement_date)
        await shot(ui, f"receive_{picking['id']}_before")
        await _click_status_button(ui, "button_validate", "receive")
        allowed = (r"khác ngày|different date|ngày.*khác", r"immediate|ngay lập tức",
                   r"backorder|đơn hàng chờ|giao sau")
        state = ""
        for _ in range(3):  # validate -> maybe a dialog -> confirm it -> wait again
            state = await _wait_state(ui, "stock.picking", picking["id"], "state", ("done", "cancel"))
            if state == "done":
                break
            await _accept_dialogs(ui, "receive", allowed=allowed)
        await shot(ui, f"receive_{picking['id']}_after")
        if state != "done":
            raise StepError(f"receive: {picking['name']} is {state!r} after Validate "
                            f"(dialogs: {await _dialog_texts(ui)})")
        print(f"  receive: {picking['name']} -> done")


def _typed_qty(value: float, decimal_point: str) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", decimal_point)


async def _set_move_quantities(ui: AsyncOdooUI, moves: list[dict], wanted: dict[int, float]) -> None:
    """Type the quantity received now on each line of the open receipt.

    Every line of this invoice gets typed, even one already right (via 0 first), so Odoo
    marks it as picked; lines of the other invoices get 0 and go to the backorder.
    """
    _, decimal_point = await _lang_format(ui)
    rows = ui.page.locator(".o_field_widget[name='move_ids_without_package'] .o_data_row")
    if await rows.count() == 0:
        rows = ui.page.locator(".o_notebook .tab-pane.active .o_field_x2many .o_data_row")
    if await rows.count() != len(moves):
        raise StepError(f"receive: the receipt shows {await rows.count()} lines, Odoo has {len(moves)}")
    for i, move in enumerate(moves):
        row = rows.nth(i)
        shown = " ".join((await row.locator("td[name='product_id']").inner_text()).split())
        expected = " ".join(move["product_id"][1].split())
        if shown != expected:
            raise StepError(f"receive: line {i + 1} shows {shown!r}, expected {expected!r}")
        target = wanted[move["id"]]
        if abs(move["quantity"] - target) > 1e-6:
            steps = [target]
        else:
            steps = [0.0, target] if target else []
        for value in steps:
            await row.locator("td[name='quantity']").click()
            box = ui.page.locator(".o_data_row.o_selected_row td[name='quantity'] input").first
            await box.wait_for(state="visible", timeout=10000)
            await box.fill(_typed_qty(value, decimal_point))
            await box.dispatch_event("change")  # commit now, so 0 -> target is a real change
            await ui.wait.for_ajax()
        print(f"  receive: line {i + 1} {expected}: {_typed_qty(target, decimal_point)} "
              f"of {_typed_qty(move['product_uom_qty'], decimal_point)}")
    await _save(ui, "receive")


async def receive_part(ui: AsyncOdooUI, po_id: int, qty_by_po_line: dict[int, float],
                       movement_date: date | None = None) -> str:
    """Receive only ``qty_by_po_line`` from the open receipt; the rest goes to a backorder.

    Returns the name of the validated receipt (the one to bill for this invoice).
    """
    info = await po_info(ui, po_id)
    pickings = await rpc(ui, "stock.picking", "read", [info["picking_ids"]],
                         fields=["name", "state", "picking_type_code", "move_ids"])
    todo = [p for p in pickings
            if p["state"] not in ("done", "cancel") and p["picking_type_code"] == "incoming"]
    if len(todo) != 1:
        raise StepError(f"receive: expected 1 open receipt on {info['name']}, found "
                        f"{[(p['name'], p['state']) for p in pickings]}")
    picking = todo[0]
    rows = await rpc(ui, "stock.move", "read", [picking["move_ids"]], fields=[
        "product_id", "purchase_line_id", "product_uom_qty", "quantity", "state"])
    by_id = {m["id"]: m for m in rows}
    moves = [by_id[i] for i in picking["move_ids"] if by_id[i]["state"] not in ("done", "cancel")]
    wanted: dict[int, float] = {}
    left = dict(qty_by_po_line)  # one PO line could have more than one move
    for m in moves:
        line_id = m["purchase_line_id"][0] if m["purchase_line_id"] else None
        take = min(left.get(line_id, 0.0), m["product_uom_qty"])
        wanted[m["id"]] = take
        if line_id in left:
            left[line_id] -= take
    if any(q > 1e-6 for q in left.values()):
        raise StepError(f"receive: {picking['name']} lacks quantities for PO lines {left}")
    whole = all(abs(wanted[m["id"]] - m["product_uom_qty"]) <= 1e-6 for m in moves)

    await open_record(ui, "stock.picking", picking["id"])
    if picking["state"] in ("draft", "confirmed", "waiting"):
        check = ui.page.locator(".o_statusbar_buttons button[name='action_assign']").locator("visible=true")
        if await check.count():
            await check.first.click()
            await _settle(ui)
            fresh = await rpc(ui, "stock.move", "read", [[m["id"] for m in moves]], fields=["quantity"])
            qty_now = {r["id"]: r["quantity"] for r in fresh}
            moves = [m | {"quantity": qty_now[m["id"]]} for m in moves]
    if not whole:
        await _set_move_quantities(ui, moves, wanted)
    if movement_date:
        await _backdate_receipt(ui, movement_date)
    await shot(ui, f"receive_{picking['id']}_before")
    await _click_status_button(ui, "button_validate", "receive")
    allowed = (r"khác ngày|different date|ngày.*khác", r"immediate|ngay lập tức",
               r"backorder|đơn hàng chờ|giao sau|đơn chờ|ít hơn|less than|nhu cầu ban đầu|initial demand")
    state = ""
    for _ in range(3):
        state = await _wait_state(ui, "stock.picking", picking["id"], "state", ("done", "cancel"))
        if state == "done":
            break
        await _accept_dialogs(ui, "receive", allowed=allowed)
    await shot(ui, f"receive_{picking['id']}_after")
    if state != "done":
        raise StepError(f"receive: {picking['name']} is {state!r} after Validate "
                        f"(dialogs: {await _dialog_texts(ui)})")

    # The validated receipt holds exactly this invoice's quantities.
    done_ids = (await rpc(ui, "stock.picking", "read", [[picking["id"]]], fields=["move_ids"]))[0]["move_ids"]
    done_moves = await rpc(ui, "stock.move", "read", [done_ids],
                           fields=["purchase_line_id", "quantity", "state"])
    received: dict[int, float] = {}
    for m in done_moves:
        if m["state"] == "done" and m["purchase_line_id"]:
            line_id = m["purchase_line_id"][0]
            received[line_id] = received.get(line_id, 0.0) + m["quantity"]
    expected = {k: v for k, v in qty_by_po_line.items() if v}
    wrong = any(abs(received.get(k, 0.0) - v) > 1e-3 for k, v in expected.items())
    extra = any(k not in expected and v > 1e-6 for k, v in received.items())
    if wrong or extra:
        raise StepError(f"receive: {picking['name']} received {received}, expected {expected}")
    print(f"  receive: {picking['name']} -> done ({len(expected)} line(s))")
    return picking["name"]


# --------------------------------------------------------------------------
# 3. bill
# --------------------------------------------------------------------------
async def _bill_ids(ui: AsyncOdooUI, po_id: int) -> list[dict]:
    info = await po_info(ui, po_id)
    if not info["invoice_ids"]:
        return []
    return await rpc(ui, "account.move", "read", [info["invoice_ids"]],
                     fields=["name", "state", "move_type", "payment_state", "amount_total"])


async def _fill_line_tax_descriptions(ui: AsyncOdooUI, text: str) -> None:
    """CC1 requires 'tax_description' on every bill line that has taxes."""
    rows = ui.page.locator(".o_field_widget[name='invoice_line_ids'] .o_data_row")
    for i in range(await rows.count()):
        row = ui.page.locator(".o_field_widget[name='invoice_line_ids'] .o_data_row").nth(i)
        cell = row.locator("td[name='tax_description']")
        if await cell.count() == 0:
            return  # column not shown: nothing we can fill from the list
        if (await cell.inner_text()).strip():
            continue
        await cell.click()
        box = ui.page.locator(
            ".o_data_row.o_selected_row td[name='tax_description'] input, "
            ".o_data_row.o_selected_row td[name='tax_description'] textarea"
        ).first
        await box.wait_for(state="visible", timeout=5000)
        await box.fill(text)
        await ui.wait.for_ajax()
        print(f"  bill: line {i + 1} tax description {text!r}")


async def _bill_date(ui: AsyncOdooUI, po_id: int, data: BillData,
                     receipt_names: list[str] | None = None) -> date:
    """The invoice date from the PDF, but never before the receipts' done date (CC1 rule)."""
    wanted = data.invoice_date or date.today()
    info = await po_info(ui, po_id)
    if not info["picking_ids"]:
        return wanted
    receipts = await rpc(ui, "stock.picking", "read", [info["picking_ids"]],
                         fields=["name", "state", "date_done"])
    if receipt_names is not None:
        receipts = [r for r in receipts if r["name"] in receipt_names]
    tz_name = await ui.page.evaluate(
        """async () => (await (await fetch('/web/session/get_session_info', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
        })).json()).result.user_context.tz"""
    )
    latest = wanted
    for r in receipts:
        if r["state"] != "done" or not r["date_done"]:
            continue
        done_utc = datetime.strptime(r["date_done"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        try:
            from zoneinfo import ZoneInfo

            local = done_utc.astimezone(ZoneInfo(tz_name or "Asia/Ho_Chi_Minh")).date()
        except Exception:
            local = (done_utc + timedelta(hours=7)).date()  # CC1 runs in Vietnam (UTC+7)
        if local > latest:
            latest = local
            print(f"  bill: receipt {r['name']} was done on {local}, after the invoice date "
                  f"{wanted}: the bill takes {local} (CC1 refuses a bill dated before its receipt)")
    return latest


async def _create_bill_from_receipts(ui: AsyncOdooUI, po_id: int, data: BillData,
                                     receipt_names: list[str] | None = None) -> None:
    """CC1 bills storable/consumable goods from their receipts, not with "Create Bill".

    Wizard "Create Invoices from Transfers": invoice date (required) + receipts to bill,
    then "Create Invoices" (action_create_invoices).
    """
    info = await po_info(ui, po_id)
    receipts = await rpc(ui, "stock.picking", "read", [info["picking_ids"]],
                         fields=["name", "state", "picking_type_code"]) if info["picking_ids"] else []
    done = [r["name"] for r in receipts if r["state"] == "done" and r["picking_type_code"] == "incoming"]
    if receipt_names is not None:
        done = [n for n in done if n in receipt_names]
    if not done:
        raise StepError(f"bill: {info['name']} has no validated receipt to bill")
    await _click_status_button(ui, "action_open_picking_invoice_wizard", "bill")
    wizard = ui.page.locator(DIALOG).last
    await wizard.wait_for(state="visible", timeout=30000)
    await ui.wait.for_all()

    if data.invoice_date:
        date_format, _ = await _lang_format(ui)
        box = wizard.locator(".o_field_widget[name='invoice_date'] input").first
        await box.click()
        await box.press("Control+a")
        await box.fill(data.invoice_date.strftime(date_format))
        await box.press("Enter")
        await ui.wait.for_ajax()

    tags = wizard.locator(".o_field_widget[name='picking_ids']")
    # The wizard may preselect every unbilled receipt: keep only the ones to bill here.
    for _ in range(20):
        extra = tags.locator(".o_tag").filter(
            has_not_text=re.compile("|".join(re.escape(n) for n in done))
        )
        if await extra.count() == 0:
            break
        print(f"  bill: wizard: removing receipt {(await extra.first.inner_text()).strip()!r}")
        await extra.first.locator(".o_delete").click()
        await ui.wait.for_ajax()
    for name in done:
        if name in await tags.inner_text():
            continue
        box = tags.locator("input").first
        await box.click()
        await box.fill(name)
        item = ui.page.locator(".o-autocomplete--dropdown-item").locator("visible=true").filter(
            has_text=name
        ).first
        try:
            await item.wait_for(state="visible", timeout=15000)
        except Exception as exc:
            offered = await ui.page.locator(".o-autocomplete--dropdown-item").all_inner_texts()
            raise StepError(f"bill: receipt {name} not offered in the wizard ({offered})") from exc
        await item.click()
        await ui.wait.for_ajax()
        print(f"  bill: wizard receipt {name}")
    await shot(ui, "bill_wizard")
    before = set(info["invoice_ids"])
    await wizard.locator("button[name='action_create_invoices']").first.click()
    for _ in range(60):
        await ui.page.wait_for_timeout(1000)
        if set((await po_info(ui, po_id))["invoice_ids"]) - before:
            break
        texts = await _dialog_texts(ui)
        if texts and not await wizard.locator("button[name='action_create_invoices']").count():
            raise StepError(f"bill: the wizard answered: {texts}")
    await _settle(ui)


async def bill(ui: AsyncOdooUI, po_id: int, data: BillData,
               receipt_names: list[str] | None = None) -> int:
    """Create (or reuse) the vendor bill of the PO, fill it from ``data`` and post it.

    With ``receipt_names`` a new bill is always made from exactly those receipts (one
    invoice of a PO that groups several); without, the PO's single bill is reused.
    """
    bills = [b for b in await _bill_ids(ui, po_id) if b["move_type"] == "in_invoice"]
    posted = [b for b in bills if b["state"] == "posted"]
    if posted and receipt_names is None:
        print(f"  bill: already posted {[b['name'] for b in posted]}, skipped")
        return posted[0]["id"]
    data = replace(data, invoice_date=await _bill_date(ui, po_id, data, receipt_names))
    drafts = [b for b in bills if b["state"] == "draft"]
    if receipt_names is not None:
        if drafts:
            raise StepError(f"bill: draft bills {[b['id'] for b in drafts]} already exist on the PO")
        before = {b["id"] for b in bills}
        await open_record(ui, "purchase.order", po_id)
        await _create_bill_from_receipts(ui, po_id, data, receipt_names)
        new = [b for b in await _bill_ids(ui, po_id) if b["id"] not in before]
        if len(new) != 1:
            raise StepError(f"bill: expected 1 new bill from {receipt_names}, got {new}")
        bill_id = new[0]["id"]
        print(f"  bill: created draft bill id={bill_id} from {receipt_names}")
        await open_record(ui, "account.move", bill_id)
    elif drafts:
        bill_id = drafts[0]["id"]
        print(f"  bill: reusing draft bill id={bill_id}")
        await open_record(ui, "account.move", bill_id)
    else:
        await open_record(ui, "purchase.order", po_id)
        await _create_bill_from_receipts(ui, po_id, data)
        bills = [b for b in await _bill_ids(ui, po_id) if b["state"] == "draft"]
        if not bills:
            raise StepError(f"bill: no draft bill after 'Create Bill' ({await _dialog_texts(ui)})")
        bill_id = bills[0]["id"]
        print(f"  bill: created draft bill id={bill_id}")
        await open_record(ui, "account.move", bill_id)

    date_format, _ = await _lang_format(ui)
    bill_date = data.invoice_date or date.today()
    typed_date = bill_date.strftime(date_format)
    po = await po_info(ui, po_id)
    description = data.description or f"Mua hàng theo {po['name']}, HĐ {data.ref}"
    filled = {
        "ref": await _fill_input(ui, "ref", data.ref),
        "serial_no": await _fill_input(ui, "serial_no", data.serial) if data.serial else False,
        "invoice_date": await _fill_input(ui, "invoice_date", typed_date),
        "description": await _fill_input(ui, "description", description),
    }
    # Due date is required when the vendor has no payment terms.
    due = ui.page.locator(".o_form_view .o_field_widget[name='invoice_date_due'] input").locator("visible=true")
    if await due.count() and not (await due.first.input_value()).strip():
        filled["invoice_date_due"] = await _fill_input(ui, "invoice_date_due", typed_date)
    # CC1: "Diễn giải thuế" is required on bills with taxes; it lives in another tab.
    tax_text = f"Thuế GTGT HĐ {data.serial or ''} số {data.ref}".replace("  ", " ")
    filled["tax_description"] = await _fill_in_any_tab(ui, "tax_description", tax_text)
    print(f"  bill: filled {filled} (date {typed_date}, serial {data.serial!r})")
    await _fill_line_tax_descriptions(ui, description)
    await _save(ui, "bill")
    await shot(ui, "bill_before_post")

    await _click_status_button(ui, "action_post", "bill")
    state = ""
    for _ in range(3):
        state = await _wait_state(ui, "account.move", bill_id, "state", ("posted", "cancel"))
        if state == "posted":
            break
        await _accept_dialogs(ui, "bill", allowed=(r"khác ngày|different date|ngày.*khác",))
    await shot(ui, "bill_after_post")
    if state != "posted":
        raise StepError(f"bill: id={bill_id} is {state!r} after Post (dialogs: {await _dialog_texts(ui)})")
    print(f"  bill: id={bill_id} posted")
    return bill_id


# --------------------------------------------------------------------------
# 4. pay (optional)
# --------------------------------------------------------------------------
async def pay(ui: AsyncOdooUI, bill_id: int) -> None:
    move = (await rpc(ui, "account.move", "read", [[bill_id]], fields=["name", "payment_state", "state"]))[0]
    if move["payment_state"] in ("paid", "in_payment"):
        print(f"  pay: {move['name']} already {move['payment_state']!r}, skipped")
        return
    if move["state"] != "posted":
        raise StepError(f"pay: {move['name']} is not posted")
    await open_record(ui, "account.move", bill_id)
    await _click_status_button(ui, "action_register_payment", "pay")
    dialog = ui.page.locator(DIALOG).last
    await dialog.wait_for(state="visible", timeout=15000)
    await shot(ui, "pay_wizard")
    create = dialog.locator("button[name='action_create_payments']").first
    await create.click()
    await _settle(ui)
    await _accept_dialogs(ui, "pay", allowed=(r"khác ngày|different date",))
    move = (await rpc(ui, "account.move", "read", [[bill_id]], fields=["payment_state"]))[0]
    if move["payment_state"] not in ("paid", "in_payment", "partial"):
        raise StepError(f"pay: payment state is {move['payment_state']!r}")
    print(f"  pay: payment state {move['payment_state']!r}")


async def complete_purchase_order_by_invoice(
    ui: AsyncOdooUI,
    po: str | int,
    parts: list[InvoicePart],
    fill_analytic: Callable[[AsyncOdooUI], Awaitable[None]],
    *,
    do_pay: bool = False,
) -> list[int]:
    """A PO grouping several vendor invoices.

    Per invoice, in the given order: receive its quantities on their own receipt, dated on
    the invoice date, then bill that receipt with the invoice's number, serial and date.
    Returns the bill ids, one per part.
    """
    po_id = await find_po(ui, po)
    info = await po_info(ui, po_id)
    print(f"\n== complete {info['name']} (id {po_id}) with {len(parts)} invoices: state "
          f"{info['state']!r}, receipt {info['receipt_status']!r}, billing {info['invoice_status']!r}")
    await confirm(ui, po_id, fill_analytic)
    bill_ids = []
    for k, part in enumerate(parts, start=1):
        print(f"\n-- invoice {k}/{len(parts)}: {part.data.serial or ''} số {part.data.ref} "
              f"({part.data.invoice_date})")
        receipt = await receive_part(ui, po_id, part.qty_by_po_line, part.data.invoice_date)
        bill_id = await bill(ui, po_id, part.data, receipt_names=[receipt])
        if do_pay:
            await pay(ui, bill_id)
        bill_ids.append(bill_id)
    final = await po_info(ui, po_id)
    print(f"== {final['name']}: state {final['state']!r}, receipt {final['receipt_status']!r}, "
          f"billing {final['invoice_status']!r}")
    return bill_ids


async def complete_purchase_order(
    ui: AsyncOdooUI,
    po: str | int,
    data: BillData | None,
    fill_analytic: Callable[[AsyncOdooUI], Awaitable[None]],
    *,
    do_pay: bool = False,
) -> dict:
    """Run confirm -> receive -> bill (-> pay) on one PO and return its final state."""
    po_id = await find_po(ui, po)
    info = await po_info(ui, po_id)
    print(f"\n== complete {info['name']} (id {po_id}): state {info['state']!r}, "
          f"receipt {info['receipt_status']!r}, billing {info['invoice_status']!r}")
    if data is None:
        if not info["partner_ref"]:
            raise StepError(f"{info['name']}: no vendor reference; pass --invoice for the bill data")
        data = BillData(ref=info["partner_ref"])
    await confirm(ui, po_id, fill_analytic)
    await receive(ui, po_id, data.invoice_date)
    bill_id = await bill(ui, po_id, data)
    if do_pay:
        await pay(ui, bill_id)
    final = await po_info(ui, po_id)
    print(f"== {final['name']}: state {final['state']!r}, receipt {final['receipt_status']!r}, "
          f"billing {final['invoice_status']!r}")
    return final
