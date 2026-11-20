"""Create a test contact (res.partner) on Odoo 17 through the UI.

Credentials and server come from environment variables (see conftest.py):
    ODOO_URL, ODOO_USER, ODOO_PASSWORD, ODOO_DB, ODOO_VERSION

Run with:
    pytest tests/test_create_partner.py -vvs -x
"""

import os
import time

from odoo_playwright.ui_async import AsyncOdooUI


async def test_create_partner(async_odoo_ui: AsyncOdooUI):
    ui = async_odoo_ui
    # Unique name per run so each execution creates a new, identifiable record
    partner_name = f"Test Partner {int(time.time())}"

    os.makedirs("screenshots", exist_ok=True)

    # Open the Contacts (res.partner) screen. This server uses a custom theme with no
    # standard app grid, so we use the direct URL from the browser. After login the
    # page is already on /web, so a hash-only change may not reload Odoo: reload it.
    await ui.navigate("/web#action=660&model=res.partner&view_type=kanban&menu_id=482")
    await ui.page.reload()
    await ui.wait.for_all()
    try:
        await ui.page.wait_for_selector(".o_list_view, .o_kanban_view", timeout=15000)
    except Exception:
        # Fallback: command palette (Ctrl+K), by Vietnamese or English app name
        for app_name in ("Liên hệ", "Contacts"):
            try:
                await ui.go_to_app(app_name)
                await ui.page.wait_for_selector(".o_list_view, .o_kanban_view", timeout=15000)
                break
            except Exception:
                continue

    # Screenshot + URL to confirm which screen the test is on before creating anything
    await ui.page.screenshot(path="screenshots/contacts_before_new.png")
    print(f"\nCurrent URL before creating: {ui.page.url}")
    # Strict guard: never create anything unless we are really on the res.partner screen
    assert "res.partner" in ui.page.url, (
        f"Not on res.partner screen (URL: {ui.page.url}), see screenshots/contacts_before_new.png"
    )

    # Create a new contact and fill the name
    # Click the New button (kanban or list), then wait for the form to open
    all_buttons = ui.page.locator("button.o_list_button_add, .o-kanban-button-new")
    print(f"New buttons in DOM: {await all_buttons.count()}")
    visible_button = ui.page.locator(
        "button.o_list_button_add:visible, .o-kanban-button-new:visible"
    ).first
    try:
        # Prefer the visible button (the DOM may also hold hidden duplicates)
        await visible_button.click(timeout=10000)
    except Exception:
        # Fallback: the button exists but the theme hides it, trigger its click handler directly
        try:
            await all_buttons.first.dispatch_event("click")
        except Exception:
            os.makedirs("screenshots", exist_ok=True)
            await ui.page.screenshot(path="screenshots/create_partner_no_new_button.png")
            raise
    await ui.page.wait_for_selector(".o_form_view", timeout=15000)
    await ui.wait.for_all()
    await ui.fill_field("name", partner_name)

    # Blur the field so Odoo marks the record dirty and shows the Save button
    await ui.page.keyboard.press("Tab")
    await ui.wait.for_all()
    await ui.page.screenshot(path="screenshots/partner_before_save.png")

    # Save: in Odoo 17 the save button only appears once the record is dirty
    save_button = ui.page.locator(".o_form_button_save:visible").first
    try:
        await save_button.click(timeout=10000)
    except Exception:
        # Fallbacks: the theme may hide the button, so trigger it directly, then Alt+S
        try:
            await ui.page.locator(".o_form_button_save").first.dispatch_event("click")
        except Exception:
            await ui.page.keyboard.press("Alt+s")
    await ui.wait.for_all()
    saved_name = await ui.get_field_value("name")
    assert saved_name == partner_name, (
        f"Expected saved partner name '{partner_name}', got '{saved_name}'"
    )
