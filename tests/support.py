"""Helpers for the live purchase tests (tests/test_purchase_order.py).

* ``OdooData``: JSON-RPC through the logged-in browser page (same session, same rights),
  remembers every record it creates and deletes them again in ``cleanup()``.
* UI helpers that ``AsyncOdooUI`` lacks: many2one/field filling inside a list row,
  a save that raises on invalid fields, the analytic distribution popup, and the
  amounts shown in the totals block. They select by ``name=`` and CSS classes, not
  by English labels, so they also work on Vietnamese UIs like CC1.
"""

from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from playwright.async_api import Locator

from odoo_playwright.ui_async import AsyncOdooUI

# Real records in a many2one dropdown; "Create ..." / "Search More..." carry o_m2o_dropdown_option.
DROPDOWN_ITEM = ".o-autocomplete--dropdown-item, .ui-autocomplete li"
ACTION_PREFIXES = ("search", "create", "start typing", "tìm", "tạo")


class OdooRPCError(Exception):
    """An error returned by Odoo's JSON-RPC; ``odoo_name`` is e.g. odoo.exceptions.AccessError."""

    def __init__(self, error: dict):
        data = error.get("data") or {}
        self.odoo_name = data.get("name") or ""
        self.odoo_message = data.get("message") or error.get("message") or ""
        super().__init__(f"{self.odoo_name}: {self.odoo_message}")


def _jsonable(value: Any) -> Any:
    """Domains are written with tuples; JSON-RPC wants lists."""
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


_RPC_JS = """async ([model, method, args, kwargs]) => {
    const res = await fetch(`/web/dataset/call_kw/${model}/${method}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({jsonrpc: '2.0', method: 'call',
                              params: {model, method, args, kwargs}}),
    });
    return await res.json();
}"""


class OdooData:
    """RPC calls as the logged-in user, plus cleanup of what the test created."""

    def __init__(self, ui: AsyncOdooUI):
        self.ui = ui
        self.token = "PWT-" + uuid.uuid4().hex[:8].upper()
        self.recorder = None
        self._created: list[tuple[str, int]] = []
        self._po_partners: list[int] = []

    async def call(self, model: str, method: str, args: list | None = None, **kwargs: Any) -> Any:
        reply = await self.ui.page.evaluate(
            _RPC_JS, [model, method, _jsonable(args or []), _jsonable(kwargs)]
        )
        if reply.get("error"):
            raise OdooRPCError(reply["error"])
        return reply.get("result")

    async def create(self, model: str, values: dict, context: dict | None = None) -> int:
        kwargs = {"context": context} if context else {}
        record_id = await self.call(model, "create", [values], **kwargs)
        if isinstance(record_id, list):
            record_id = record_id[0]
        self._created.append((model, record_id))
        return record_id

    async def records(self, model: str, domain: list, fields: list[str]) -> list[dict]:
        return await self.call(model, "search_read", [domain], fields=fields)

    def register_purchase_orders(self, partner_id: int) -> None:
        """Purchase orders of this partner are cancelled and deleted in cleanup()."""
        self._po_partners.append(partner_id)

    async def cleanup(self) -> list[str]:
        """Delete everything this test created (archive what Odoo refuses to delete)."""
        problems: list[str] = []
        if self._po_partners:
            try:
                po_ids = await self.call(
                    "purchase.order", "search", [[("partner_id", "in", self._po_partners)]]
                )
            except OdooRPCError as exc:
                po_ids = []
                problems.append(f"search purchase.order: {exc}")
            for po_id in po_ids:
                for method in ("button_unlock", "button_cancel"):
                    try:
                        await self.call("purchase.order", method, [[po_id]])
                    except OdooRPCError:
                        pass
                try:
                    await self.call("purchase.order", "unlink", [[po_id]])
                except OdooRPCError as exc:
                    problems.append(f"purchase.order {po_id}: {exc}")
        for model, record_id in reversed(self._created):
            try:
                await self.call(model, "unlink", [[record_id]])
            except OdooRPCError as exc:
                try:
                    await self.call(model, "write", [[record_id], {"active": False}])
                    problems.append(f"{model} {record_id}: archived, not deleted ({exc.odoo_message})")
                except OdooRPCError:
                    problems.append(f"{model} {record_id}: left in the database ({exc.odoo_message})")
        self._created.clear()
        for line in problems:
            print("  cleanup:", line)
        return problems


async def unambiguous_record(
    data: OdooData,
    model: str,
    *,
    label: str,
    env_var: str,
    extra_domain: list | None = None,
) -> tuple[int, str]:
    """(id, display name) of the record to use for a required field.

    ``$env_var`` may hold an id or an exact name. Otherwise the first record matching
    ``extra_domain`` is used (the user's rule for required fields: first value).
    """
    domain = list(extra_domain or [])
    wanted = os.getenv(env_var, "").strip()
    if wanted:
        domain.append(("id", "=", int(wanted)) if wanted.isdigit() else ("name", "=", wanted))
    rows = await data.call(model, "search_read", [domain], fields=["display_name"], limit=2)
    if not rows:
        raise AssertionError(f"No {label} ({model}) found for {domain}; set {env_var}")
    if wanted and len(rows) > 1:
        raise AssertionError(f"{env_var}={wanted!r} matches several {label} records")
    return rows[0]["id"], rows[0]["display_name"]


async def mandatory_analytic_accounts(data: OdooData, business_domain: str) -> dict[str, tuple[int, str]]:
    """{plan name: (account id, account name)} for every analytic plan mandatory on that domain."""
    try:
        plans = await data.call(
            "account.analytic.plan", "search_read", [[("parent_id", "=", False)]],
            fields=["name", "default_applicability"],
        )
        rules = await data.call(
            "account.analytic.applicability", "search_read",
            [[("business_domain", "=", business_domain)]],
            fields=["analytic_plan_id", "applicability"],
        )
    except OdooRPCError as exc:
        print(f"  analytic: could not read applicability rules ({exc}), assuming none mandatory")
        return {}
    override = {r["analytic_plan_id"][0]: r["applicability"] for r in rules if r["analytic_plan_id"]}
    result: dict[str, tuple[int, str]] = {}
    for plan in plans:
        if override.get(plan["id"], plan.get("default_applicability")) != "mandatory":
            continue
        accounts = await data.call(
            "account.analytic.account", "search_read",
            [["|", ("root_plan_id", "=", plan["id"]), ("plan_id", "=", plan["id"])]],
            fields=["name"], limit=1,
        )
        if accounts:
            result[plan["name"]] = (accounts[0]["id"], accounts[0]["name"])
    return result


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------
_step = 0


async def show_step(ui: AsyncOdooUI, text: str) -> None:
    """Print the step and save screenshots/purchase_step_<n>.png."""
    global _step
    _step += 1
    print(f"\n[{_step}] {text}")
    Path("screenshots").mkdir(exist_ok=True)
    try:
        await ui.page.screenshot(path=f"screenshots/purchase_step_{_step:02d}.png", full_page=True)
    except Exception:
        pass


async def close_dropdowns(ui: AsyncOdooUI) -> None:
    """An autocomplete left open swallows the next click (seen on CC1's 'Giao hàng đến')."""
    page = ui.page
    open_menus = page.locator(f"{DROPDOWN_ITEM}, .o_popover").locator("visible=true")
    for _ in range(3):
        if await open_menus.count() == 0:
            return
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)


async def wait_dropdown_loaded(ui: AsyncOdooUI, timeout: int = 10000) -> None:
    """Odoo first shows a 'Loading...' / 'Đang tải...' item; wait for the real results."""
    try:
        await ui.page.wait_for_function(
            """(sel) => {
                const items = [...document.querySelectorAll(sel)].filter(e => e.offsetParent !== null);
                return items.length > 0 && !items.some(e => /^(đang tải|loading)/i.test(e.innerText.trim()));
            }""",
            arg=DROPDOWN_ITEM,
            timeout=timeout,
        )
    except Exception:
        pass  # the caller reports what the dropdown offered


def _field_input(ui: AsyncOdooUI, field: str, within: Locator | None) -> Locator:
    scope = within if within is not None else ui.page.locator(".o_form_view").first
    return scope.locator(f".o_field_widget[name='{field}'] input").first


async def fill_many2one(ui: AsyncOdooUI, field: str, value: str, within: Locator | None = None) -> None:
    """Type ``value`` and click the record whose name equals it (or contains it).

    Raises ValueError when Odoo offers no such record.
    """
    page = ui.page
    field_input = _field_input(ui, field, within)
    await field_input.click()
    await field_input.fill(value)
    items = page.locator(DROPDOWN_ITEM).locator("visible=true")
    try:
        await items.first.wait_for(state="visible", timeout=8000)
    except Exception as exc:
        raise ValueError(f"{field}: no dropdown for {value!r}") from exc
    await wait_dropdown_loaded(ui)

    def norm(s: str) -> str:
        # CC1 shows "Name ‒ <tax id>"; codes appear as "[CODE] Name".
        s = re.sub(r"\s+[‒–—-]\s*[\d-]+\s*$", "", s)
        return re.sub(r"\s+", " ", s).strip().lower()

    wanted = norm(value)
    texts = [" ".join(t.split()) for t in await items.all_inner_texts()]
    classes = [await items.nth(i).get_attribute("class") or "" for i in range(len(texts))]
    real = [
        i for i, t in enumerate(texts)
        if "o_m2o_dropdown_option" not in classes[i] and not t.lower().startswith(ACTION_PREFIXES)
    ]
    exact = [i for i in real if norm(texts[i]) == wanted or norm(texts[i]).endswith("] " + wanted)]
    partial = [i for i in real if wanted in norm(texts[i])]
    chosen = (exact or partial or [None])[0]
    if chosen is None:
        await page.keyboard.press("Escape")
        raise ValueError(f"{field}: no record named {value!r}; dropdown offered {texts}")
    await items.nth(chosen).click()
    await ui.wait.for_all()


async def _decimal_point(data_or_ui: AsyncOdooUI) -> tuple[str, str]:
    """(decimal point, thousands separator) of the logged-in user's language."""
    forced = os.getenv("ODOO_DECIMAL_POINT")
    if forced:
        return forced, "." if forced == "," else ","
    data = OdooData(data_or_ui)
    try:
        info = await data.ui.page.evaluate(
            """async () => (await (await fetch('/web/session/get_session_info', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}}),
            })).json()).result.user_context.lang"""
        )
        rows = await data.call(
            "res.lang", "search_read", [[("code", "=", info)]], fields=["decimal_point", "thousands_sep"]
        )
        return rows[0]["decimal_point"], rows[0]["thousands_sep"]
    except Exception:
        return ".", ","


async def fill_field(ui: AsyncOdooUI, field: str, value: Any, within: Locator | None = None) -> None:
    """Fill a plain input (numbers are typed with the user's decimal point)."""
    text = str(value)
    if isinstance(value, (float, Decimal)):
        point, _ = await _decimal_point(ui)
        text = format(value, "f").rstrip("0").rstrip(".").replace(".", point)
    field_input = _field_input(ui, field, within)
    await field_input.click()
    await field_input.press("Control+a")
    await field_input.fill(text)
    await field_input.press("Tab")
    await ui.wait.for_ajax()


async def save(ui: AsyncOdooUI) -> None:
    """Save the form (button, else Alt+S). Raises ValueError("invalid fields ...") on refusal."""
    page = ui.page
    await close_dropdowns(ui)
    button = page.locator(".o_form_button_save").locator("visible=true").first
    if await button.count():
        await button.click()
    else:
        await page.keyboard.press("Alt+s")
    await ui.wait.for_all()
    await page.wait_for_timeout(500)
    invalid = page.locator(".o_form_view .o_field_invalid")
    if await invalid.count():
        names = [await invalid.nth(i).get_attribute("name") for i in range(await invalid.count())]
        raise ValueError(f"invalid fields, Odoo refused to save: {names}")
    try:
        await page.wait_for_function("() => /[#&?/]id=\\d+|\\/\\d+(\\?|$)/.test(location.href)",
                                     timeout=10000)
    except Exception as exc:
        raise ValueError(f"invalid save: the record got no id ({page.url})") from exc
    await page.locator(".o_form_button_save").locator("visible=true").first.wait_for(
        state="hidden", timeout=10000
    )


async def discard(ui: AsyncOdooUI) -> None:
    page = ui.page
    await close_dropdowns(ui)
    button = page.locator(".o_form_button_cancel").locator("visible=true").first
    if await button.count():
        await button.click()
    else:
        await page.keyboard.press("Alt+j")
    await ui.wait.for_all()
    # Odoo may ask to confirm discarding a new record.
    confirm = page.locator(".modal.show .modal-footer .btn-primary").first
    if await confirm.count():
        await confirm.click()
        await ui.wait.for_all()


async def add_order_line(ui: AsyncOdooUI) -> Locator:
    """Click the first 'Add a product' link of order_line and return the row being edited."""
    page = ui.page
    await page.locator(".o_field_widget[name='order_line'] .o_field_x2many_list_row_add a").first.click()
    row = page.locator(".o_field_widget[name='order_line'] .o_data_row.o_selected_row")
    await row.wait_for(state="visible", timeout=10000)
    return row


async def fill_analytic_distribution(
    ui: AsyncOdooUI, field: str, accounts: dict[str, str], within: Locator | None = None
) -> None:
    """Open the analytic popup and choose ``accounts[plan name]`` in each plan's table.

    Raises ValueError when a plan table or account cannot be found.
    """
    page = ui.page
    scope = within if within is not None else page.locator(".o_form_view").first
    await scope.locator(f".o_field_widget[name='{field}']").first.click()
    popup = page.locator(".analytic_distribution_popup").locator("visible=true").first
    await popup.wait_for(state="visible", timeout=8000)
    for plan, account in accounts.items():
        table = popup.locator("table").filter(has=page.locator("th", has_text=plan)).first
        if await table.count() == 0:
            raise ValueError(f"analytic popup has no table for plan {plan!r}")
        empty_input = None
        inputs = table.locator("input.o-autocomplete--input")
        for i in range(await inputs.count()):
            if not await inputs.nth(i).input_value():
                empty_input = inputs.nth(i)
                break
        if empty_input is None:
            continue  # already filled
        await empty_input.click()
        await empty_input.fill(account)
        items = page.locator(DROPDOWN_ITEM).locator("visible=true")
        await items.first.wait_for(state="visible", timeout=8000)
        await wait_dropdown_loaded(ui)
        texts = [" ".join(t.split()).lower() for t in await items.all_inner_texts()]
        match = next((i for i, t in enumerate(texts) if account.lower() in t), None)
        if match is None:
            raise ValueError(f"analytic plan {plan!r}: no account {account!r}; offered {texts}")
        await items.nth(match).click()
        await ui.wait.for_ajax()
    # Clicking outside the popup closes it and keeps the row in edit mode.
    target = scope.locator(".o_field_widget[name='product_qty']").first
    if await target.count():
        await target.click()
    else:
        await page.keyboard.press("Escape")
    await ui.wait.for_ajax()


async def displayed_amounts(ui: AsyncOdooUI) -> dict[str, Decimal]:
    """amount_untaxed / amount_tax / amount_total as displayed on the form.

    Uses fields with those names when the form has them, otherwise the tax_totals block:
    first row = untaxed, last row = total, rows in between = taxes.
    """
    point, sep = await _decimal_point(ui)

    def to_decimal(text: str) -> Decimal:
        digits = re.sub(rf"[^\d{re.escape(point)}{re.escape(sep)}-]", "", text)
        digits = digits.replace(sep, "").replace(point, ".") if sep else digits.replace(point, ".")
        return Decimal(digits or "0")

    page = ui.page
    result: dict[str, Decimal] = {}
    for name in ("amount_untaxed", "amount_tax", "amount_total"):
        widget = page.locator(f".o_form_view .o_field_widget[name='{name}']").first
        if await widget.count() and await widget.is_visible():
            result[name] = to_decimal(await widget.inner_text())
    if len(result) == 3:
        return result
    amounts = await page.evaluate(
        """() => {
            const box = document.querySelector(".o_form_view .o_field_widget[name='tax_totals']");
            if (!box) return [];
            return [...box.querySelectorAll('tr')]
                .map(tr => [...tr.querySelectorAll('td')].pop())
                .filter(td => td && /\\d/.test(td.innerText))
                .map(td => td.innerText.trim());
        }"""
    )
    if len(amounts) >= 2:
        values = [to_decimal(a) for a in amounts]
        result.setdefault("amount_untaxed", values[0])
        result.setdefault("amount_total", values[-1])
        result.setdefault("amount_tax", sum(values[1:-1], Decimal(0)))
    return result
