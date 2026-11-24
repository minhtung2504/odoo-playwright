"""Live purchase flow: RFQ, confirmation, tax, lock/cancel and role checks."""
import os
from decimal import Decimal
from uuid import uuid4

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from odoo_playwright.ui_async import AsyncOdooUI
from tests.support import (
    OdooData,
    OdooRPCError,
    add_order_line,
    close_dropdowns,
    discard,
    displayed_amounts,
    fill_analytic_distribution,
    fill_field,
    fill_many2one,
    mandatory_analytic_accounts,
    save,
    show_step,
    unambiguous_record,
)

pytestmark = pytest.mark.integration


async def open_purchases(ui):
    # Default: Purchase > Requests for Quotation by action xmlid (works in any UI language).
    path = os.getenv("PURCHASE_PATH", "web#action=purchase.purchase_rfq&view_type=list").strip()
    if path:
        await ui.navigate(path)
    else:
        await ui.go_to_app(os.getenv("PURCHASE_APP", "Purchase"))
    await expect(ui.page.locator(".o_list_view, .o_kanban_view").first).to_be_visible()


async def contract_requirements(data):
    """Billing Journal shows a required asterisk on this live form regardless of the
    is_required_journal flag's own default, so this always supplies one when the field exists.

    Type (contract_type_id) is documented as "cần BA xác nhận" for which categories are
    mandatory, so this test does not force a value for it.
    """
    present = await data.call("purchase.order", "fields_get", [["journal_id"]], attributes=["relation"])
    required = {}
    if "journal_id" in present:
        required["journal_id"] = await unambiguous_record(
            data, "account.journal", label="Nhật ký hóa đơn mua", env_var="ODOO_TEST_PURCHASE_JOURNAL",
            extra_domain=[("type", "=", "purchase")])
    return required


@pytest.fixture
async def purchase_seed(odoo_data):
    data = odoo_data
    vendor = data.token + "-vendor"
    partner_id = await data.create("res.partner", {"name": vendor, "supplier_rank": 1})
    tax_id = await data.create("account.tax", {"name": data.token + "-ptax10",
        "amount": 10, "amount_type": "percent", "type_tax_use": "purchase", "price_include": False})
    category_id = await data.create("product.category", {"name": data.token + "-pcategory"})
    product = data.token + "-pservice"
    template_id = await data.create("product.template", {"name": product,
        "default_code": data.token + "-psku", "categ_id": category_id, "detailed_type": "service",
        "sale_ok": False, "purchase_ok": True, "standard_price": 50000,
        "supplier_taxes_id": [(6, 0, [tax_id])], "taxes_id": [(6, 0, [])]})
    templates = await data.call("product.template", "read", [[template_id]], fields=["product_variant_id"])
    product_id = templates[0]["product_variant_id"][0]
    contracts = await contract_requirements(data)
    analytic = await mandatory_analytic_accounts(data, "purchase_order")
    data.register_purchase_orders(partner_id)
    return dict(vendor=vendor, partner_id=partner_id, product=product,
                product_id=product_id, tax_id=tax_id, contracts=contracts, analytic=analytic)


async def create_purchase_order(ui, seed, qty=2, price=50000):
    await open_purchases(ui)
    await show_step(ui, "Tạo yêu cầu báo giá mua test")
    await ui.click_create()
    await fill_many2one(ui, "partner_id", seed["vendor"])
    for field, (_, label) in seed.get("contracts", {}).items():
        if await ui.page.locator(".o_form_view [name='" + field + "']").count():
            await fill_many2one(ui, field, label)
    row = await add_order_line(ui)
    product_field = "product_template_id" if await row.locator(
        ".o_field_widget[name=product_template_id]").count() else "product_id"
    await fill_many2one(ui, product_field, seed["product"], within=row)
    await fill_field(ui, "product_qty", qty, within=row)
    await fill_field(ui, "price_unit", price, within=row)
    await save(ui)


async def apply_analytic_distribution(ui, seed):
    """If CC1 requires an analytic distribution per plan on purchase lines too."""
    row = ui.page.locator("[name=order_line] .o_data_row").first
    if not await row.locator(".o_field_widget[name=analytic_distribution]").count():
        return
    accounts = seed.get("analytic") or {}
    if not accounts:
        pytest.skip("No uniquely named analytic account for the plans CC1 requires on purchases")
    await row.click()
    try:
        await fill_analytic_distribution(ui,
            "analytic_distribution", {column: name for column, (_, name) in accounts.items()}, within=row)
    except (ValueError, PlaywrightTimeoutError):
        # The plan/account pairing CC1's applicability config marks mandatory for this
        # business domain does not resolve to a selectable option on a purchase line's
        # popup in this install (confirmed: the popup shows the right plan columns, but
        # searching the account CC1 names for that plan turns up no match) -- needs
        # BA/admin confirmation of the real purchase analytic setup, so this test does not
        # guess at a different account.
        await discard(ui)
        pytest.skip("Mandatory purchase analytic account did not resolve to a selectable option")
    await save(ui)


async def confirm_order(ui, timeout=10000):
    """Confirm, turning Odoo's refusal dialog into a readable failure.

    The "requires a 100% analytic distribution" check renders client-side with no network
    round trip, so it can still be a beat behind wait.for_all(); poll briefly for the dialog
    instead of taking an immediate absence as proof none is coming.
    """
    await close_dropdowns(ui)
    await ui.page.locator("button[name=button_confirm]:visible").first.click()
    await ui.wait.for_all()
    dialog = ui.page.locator(".modal-dialog:visible")
    try:
        await dialog.first.wait_for(state="visible", timeout=2000)
    except PlaywrightTimeoutError:
        return
    message = " ".join((await dialog.first.inner_text()).split())
    await dialog.first.get_by_role("button").last.click(timeout=timeout)
    raise AssertionError("Odoo refused to confirm the purchase order: " + message[:300])


async def assert_order(ui, data, seed, *, qty, tax_rate, state):
    contracts = seed.get("contracts", {})
    fields = ["id", "partner_id", "order_line", "state", "amount_untaxed", "amount_tax", "amount_total",
              *contracts]
    domain = [("partner_id", "=", seed["partner_id"])]
    # This form's breadcrumb can still read "New" right after a successful save, so the
    # created record briefly lags the client-side wait.for_all(); poll a few times instead
    # of failing on that race.
    rows = await data.records("purchase.order", domain, fields)
    for _ in range(9):
        if rows:
            break
        await ui.page.wait_for_timeout(500)
        rows = await data.records("purchase.order", domain, fields)
    assert len(rows) == 1, "Expected exactly one test purchase order"
    order = rows[0]
    assert order["partner_id"][0] == seed["partner_id"]
    expected_states = (state,) if isinstance(state, str) else tuple(state)
    assert order["state"] in expected_states, (
        "Expected state in " + repr(expected_states) + ", got " + repr(order["state"]))
    for field, (record_id, _) in contracts.items():
        assert order[field] and order[field][0] == record_id, "Wrong " + field + " on the saved order"
    lines = await data.call("purchase.order.line", "read", [order["order_line"]],
        fields=["product_id", "product_qty", "price_unit", "taxes_id"])
    assert len(lines) == 1
    line = lines[0]
    assert line["product_id"][0] == seed["product_id"]
    assert Decimal(str(line["product_qty"])) == Decimal(qty)
    assert Decimal(str(line["price_unit"])) == Decimal("50000")
    assert line["taxes_id"] == ([seed["tax_id"]] if tax_rate else [])
    untaxed = Decimal(qty) * Decimal("50000")
    tax = (untaxed * Decimal(tax_rate) / 100).quantize(Decimal(".01"))
    displayed = await displayed_amounts(ui)
    for field, expected in (("amount_untaxed", untaxed), ("amount_tax", tax), ("amount_total", untaxed + tax)):
        assert Decimal(str(order[field])).quantize(Decimal(".01")) == expected.quantize(Decimal(".01"))
        assert field in displayed, "The purchase form does not show " + field
        assert displayed[field] == expected, (
            "Form shows " + str(displayed[field]) + " for " + field + ", expected " + str(expected))
    if data.recorder:
        await data.recorder.capture(ui, "Đối chiếu đơn mua đã lưu: " + state, order=order, lines=lines,
            expected={"qty": qty, "untaxed": str(untaxed), "tax": str(tax), "total": str(untaxed + tax)})
    return order


async def test_create_edit_confirm_purchase_order(async_odoo_ui, odoo_data, purchase_seed):
    ui, data, seed = async_odoo_ui, odoo_data, purchase_seed
    await create_purchase_order(ui, seed)
    await assert_order(ui, data, seed, qty=2, tax_rate=10, state="draft")
    await show_step(ui, "Sửa số lượng và kiểm tra lại tổng tiền")
    await ui.page.locator("[name=order_line] .o_data_row").first.click()
    await fill_field(ui, "product_qty", 3)
    await save(ui)
    await assert_order(ui, data, seed, qty=3, tax_rate=10, state="draft")
    await show_step(ui, "Cập nhật phân bổ phân tích cho dòng đơn mua")
    await apply_analytic_distribution(ui, seed)
    await show_step(ui, "Xác nhận đơn mua hàng test")
    await confirm_order(ui)
    # "purchase"/"to approve" depend on the two-step approval limit; "done" means the
    # company also auto-locks an order as soon as it confirms (po_lock = 'lock').
    await assert_order(ui, data, seed, qty=3, tax_rate=10, state=("purchase", "to approve", "done"))


async def test_zero_tax_purchase_order(async_odoo_ui, odoo_data, purchase_seed):
    await odoo_data.call("product.product", "write", [[purchase_seed["product_id"]], {"supplier_taxes_id": [(6, 0, [])]}])
    await create_purchase_order(async_odoo_ui, purchase_seed)
    await assert_order(async_odoo_ui, odoo_data, purchase_seed, qty=2, tax_rate=0, state="draft")


async def test_purchase_order_requires_vendor(async_odoo_ui):
    """Saving an RFQ with no vendor must be refused, not silently accepted."""
    ui = async_odoo_ui
    await open_purchases(ui)
    await show_step(ui, "Tạo RFQ test không chọn nhà cung cấp")
    await ui.click_create()
    with pytest.raises(ValueError, match="invalid"):
        await save(ui)
    await expect(ui.page.locator(".o_field_invalid[name=partner_id]")).to_be_visible()
    await discard(ui)


async def test_lock_blocks_line_edit_then_cancel(async_odoo_ui, odoo_data, purchase_seed):
    """A confirmed order that gets locked must refuse line edits until unlocked, then cancel cleanly."""
    ui, data, seed = async_odoo_ui, odoo_data, purchase_seed
    await create_purchase_order(ui, seed)
    await apply_analytic_distribution(ui, seed)
    await show_step(ui, "Xác nhận đơn mua test")
    await confirm_order(ui)
    lock_button = ui.page.locator("button[name=button_lock]:visible").first
    unlock_button = ui.page.locator("button[name=button_unlock]:visible").first
    # Some companies auto-lock (po_lock='lock') as soon as the order confirms, so there is
    # no separate "Lock" click to make here; either way, end up unlocked before cancelling.
    if not await unlock_button.count() and await lock_button.count():
        await show_step(ui, "Khóa đơn mua test")
        await lock_button.click()
        await ui.wait.for_all()
    if await unlock_button.count():
        await expect(ui.page.locator("[name=order_line] .o_data_row").first
            .locator(".o_field_widget[name=product_qty] input")).to_have_count(0)
        await show_step(ui, "Mở khóa đơn mua test")
        await unlock_button.click()
        await ui.wait.for_all()
    await show_step(ui, "Hủy đơn mua test")
    await ui.page.locator("button[name=button_cancel]:visible").first.click()
    await ui.wait.for_all()
    order = await data.records("purchase.order", [("partner_id", "=", seed["partner_id"])], ["id", "state"])
    assert len(order) == 1 and order[0]["state"] == "cancel"


async def xmlid(data, module, name):
    rows = await data.call("ir.model.data", "search_read",
                           [[("module", "=", module), ("name", "=", name)]], fields=["res_id"], limit=1)
    assert rows, "Missing Odoo record " + module + "." + name
    return rows[0]["res_id"]


@pytest.fixture
async def readonly_purchase_login(odoo_data):
    """The read-only account this case signs in as.

    Normally ODOO_READONLY_USER/ODOO_READONLY_PASSWORD name an existing account. Only when
    ODOO_ALLOW_TEMP_USER=true does the test create a throwaway user and group and delete
    them again: never create logins on a shared database without being asked to.
    """
    configured = os.getenv("ODOO_READONLY_USER", "").strip()
    if configured:
        return configured, os.getenv("ODOO_READONLY_PASSWORD", "")
    if os.getenv("ODOO_ALLOW_TEMP_USER", "").strip().lower() not in ("1", "true", "yes"):
        pytest.skip("Set ODOO_READONLY_USER/PASSWORD, or ODOO_ALLOW_TEMP_USER=true to create one")
    data = odoo_data
    if not await data.call("res.users", "check_access_rights", ["create"], raise_exception=False):
        pytest.skip("This account may not create the temporary read-only user")
    employees = await xmlid(data, "base", "group_user")
    group_id = await data.create("res.groups", {"name": data.token + "-readonly-purchase",
                                                "implied_ids": [(6, 0, [employees])]})
    model = await data.call("ir.model", "search_read", [[("model", "=", "purchase.order")]],
                            fields=["id"], limit=1)
    await data.create("ir.model.access", {"name": data.token + "-purchase-order-read",
        "model_id": model[0]["id"], "group_id": group_id,
        "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False})
    login = data.token.lower() + "-po@example.invalid"
    password = uuid4().hex
    await data.create("res.users", {"name": data.token + "-readonly-po", "login": login,
                                    "password": password, "groups_id": [(6, 0, [employees, group_id])]},
                      context={"no_reset_password": True})
    return login, password


@pytest.mark.permissions
async def test_readonly_user_cannot_create_purchase_order(async_browser, browser_context_args, odoo_config,
                                                           odoo_data, purchase_seed, readonly_purchase_login):
    username, password = readonly_purchase_login
    if not password:
        pytest.skip("ODOO_READONLY_USER is set without ODOO_READONLY_PASSWORD")
    context = await async_browser.new_context(**browser_context_args)
    ui = AsyncOdooUI(await context.new_page(), odoo_config.base_url, odoo_config.version)
    readonly_data = OdooData(ui)
    try:
        await ui.login(username, password, odoo_config.database)
        assert await readonly_data.call("purchase.order", "check_access_rights", ["read"], raise_exception=False)
        assert not await readonly_data.call("purchase.order", "check_access_rights", ["create"], raise_exception=False)
        await open_purchases(ui)
        await expect(ui.page.locator(ui.selectors.get("button_create"))).to_have_count(0)
        with pytest.raises(OdooRPCError) as rejected:
            await readonly_data.call("purchase.order", "create", [{"partner_id": purchase_seed["partner_id"]}])
        assert rejected.value.odoo_name.endswith("AccessError")
        assert await odoo_data.call("purchase.order", "search_count",
            [[("partner_id", "=", purchase_seed["partner_id"])]]) == 0
    finally:
        await context.close()
