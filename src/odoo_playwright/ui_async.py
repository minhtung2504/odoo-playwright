"""Async version of Odoo UI class."""

import asyncio
import re
import urllib.parse
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

from playwright.async_api import Locator, Page

from odoo_playwright.selectors import get_selectors
from odoo_playwright.wait import AsyncWaitHelper


class AsyncOdooUI:
    """Async main class for interacting with Odoo UI using Playwright."""

    def __init__(
        self,
        page: Page,
        base_url: str = "http://localhost:8069",
        version: int = 17,
    ):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.version = version
        self.selectors = get_selectors(version)
        self.wait = AsyncWaitHelper(page)
        self._current_model: Optional[str] = None

    def url(self, path: str = "") -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def navigate(self, path: str = "") -> None:
        await self.page.goto(self.url(path))
        await self.wait.for_all()

    async def login(
        self,
        username: str,
        password: str,
        database: Optional[str] = None,
    ) -> None:
        await self.page.goto(self.url("/web"))

        db_selector = self.page.locator("#db, select[name='db']")
        if await db_selector.count() > 0 and database:
            await db_selector.select_option(database)
        elif await db_selector.count() > 0:
            await db_selector.first.click()
            await self.page.keyboard.press("ArrowDown")
            await self.page.keyboard.press("Tab")

        await self.page.locator("#login").fill(username)
        await self.page.locator("#password").fill(password)
        await self.page.locator("button.btn.btn-primary:not(.oe_search_button)").click()

        await self.wait.for_all()
        await self.page.wait_for_url("**/web**")

    async def logout(self) -> None:
        await self.page.locator(".o_user_menu, .oe_topbar_name").click()
        await self.page.get_by_text("Log out", exact=True).click()
        await self.wait.for_all()

    async def get_url_fragments(self) -> dict[str, str]:
        url = self.page.url
        parsed = urllib.parse.urlparse(url)
        fragment = parsed.fragment or parsed.query

        result = {}
        if fragment:
            for part in fragment.split("&"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    result[key] = urllib.parse.unquote(value)
        return result

    async def get_current_model(self) -> Optional[str]:
        fragments = await self.get_url_fragments()
        if "model" in fragments:
            return fragments["model"]

        model_input = self.page.locator("input[name='model'], [data-model]")
        if await model_input.count() > 0:
            return await model_input.first.get_attribute("value") or await model_input.first.get_attribute("data-model")

        return self._current_model

    async def go_to_app(self, app_name: str, timeout: int = 10000) -> None:
        await self.wait.for_all()
        await self.page.keyboard.press("ControlOrMeta+k")  # Cmd+K trên Mac, Ctrl+K trên Windows/Linux
        palette_input = self.page.locator(".o_command_palette input")
        await palette_input.wait_for(state="visible", timeout=timeout)
        await palette_input.fill(f"/{app_name}")
        await self.page.keyboard.press("Enter")
        await self.wait.for_all()
        await self.page.wait_for_selector(".o_content, .o_action_manager", timeout=timeout)

    async def go_to_menu(self, *menu_path: str, timeout: int = 10000) -> None:
        if len(menu_path) == 0:
            return

        await self.wait.for_all()

        menu_items = list(menu_path)
        first_item = menu_items.pop(0)

        await self.page.get_by_text(first_item, exact=True).first.click()
        await self.wait.for_all()

        for item in menu_items:
            menu_locator = self.page.locator(
                ".o_submenu, .oe_secondary_menu, .o_menu_entry_lvl_2, .o_menu_entry_lvl_3"
            ).get_by_text(item, exact=True).first
            await menu_locator.click()
            await self.wait.for_all()

        await self.page.wait_for_selector(".o_content, .o_view_controller", timeout=timeout)

    async def switch_view(self, view_type: str) -> None:
        view_button = self.page.locator(
            f"[data-view-type='{view_type}'], button[title*='{view_type}'], .o_cp_switch_buttons button[data-view-type='{view_type}']"
        )
        await view_button.click()
        await self.wait.for_all()

    async def get_current_view_type(self) -> Optional[str]:
        fragments = await self.get_url_fragments()
        return fragments.get("view_type")

    async def click_create(self, timeout: int = 10000) -> None:
        selector = self.selectors.get("button_create") + ":not([disabled])"
        buttons = self.page.locator(selector)
        clicked = False
        try:
            count = await buttons.count()
            for i in range(count):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    await btn.scroll_into_view_if_needed(timeout=timeout)
                    await btn.click(timeout=timeout)
                    clicked = True
                    break
        except Exception:
            clicked = False
        if not clicked:
            await self.page.keyboard.press("c")
        await self.wait.for_all()

    async def click_save(self, timeout: int = 10000) -> None:
        save_btn = self.page.locator(self.selectors.get("button_save"))
        await save_btn.click()
        await self.wait.for_all()

    async def click_edit(self, timeout: int = 10000) -> None:
        edit_btn = self.page.locator(self.selectors.get("button_edit"))
        await edit_btn.click()
        await self.wait.for_all()

    async def click_discard(self, timeout: int = 10000) -> None:
        discard_btn = self.page.locator(self.selectors.get("button_discard"))
        await discard_btn.click()
        await self.wait.for_all()

    async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
        try:
            delete_btn = self.page.locator(
                self.selectors.get("button_delete") + ":has-text('Delete')"
            )
            if await delete_btn.count() > 0:
                await delete_btn.click()
            else:
                # Fallback: check action menu in dropdown
                await self.page.locator(".o_cp_action_menus button").click()
                await self.page.get_by_text("Delete", exact=True).click()
        except Exception:
            # Final fallback: try the selector directly
            delete_btn = self.page.locator(self.selectors.get("button_delete"))
            await delete_btn.click()

        if confirm:
            self.page.on("dialog", lambda dialog: dialog.accept())
            await self.wait.for_all()

    async def click_action(self, action_name: str) -> None:
        await self.page.locator(self.selectors.get("button_action")).click()
        await self.page.get_by_text(action_name, exact=True).click()
        await self.wait.for_all()

    async def click_button(self, button_name: str, by_aria_label: bool = False) -> None:
        if by_aria_label:
            await self.page.get_by_role("button", name=button_name).click()
        else:
            await self.page.get_by_role("button", name=button_name, exact=True).click()
        await self.wait.for_all()

    def get_field(self, field_name: str) -> Locator:
        # Odoo 17+ uses 'name' attribute on field widget div, not on inputs
        # Field structure: <div class="o_field_widget" name="field_name"> <input /> </div>
        field_widget = self.page.locator(f".o_field_widget[name='{field_name}']").first

        # Return the input inside the field widget, or the widget itself for non-input fields
        input_in_widget = field_widget.locator("input, textarea, select").first

        # Try the input first, then fallback to the widget
        return input_in_widget

    async def get_field_value(self, field_name: str) -> str:
        field = self.get_field(field_name)

        tag = await field.evaluate("el => el.tagName.toLowerCase()")
        input_type = await field.get_attribute("type") or ""

        if tag == "select":
            option = field.locator("option:checked").first
            if await option.count() > 0:
                return await option.inner_text()
            return await field.get_attribute("data-value") or ""
        elif input_type == "checkbox":
            return str(await field.is_checked())
        elif tag == "input" or tag == "textarea":
            return await field.input_value()
        else:
            return await field.inner_text()

    async def fill_field(self, field_name: str, value: Any, timeout: int = 30000) -> None:
        field = self.get_field(field_name)

        try:
            await field.wait_for(state="visible", timeout=timeout)
        except Exception:
            # Wait a bit more for the form to load, then try to get available fields
            await asyncio.sleep(1)

            available_fields = await self.page.evaluate("""
                () => {
                    const fields = [];
                    document.querySelectorAll('input[name], textarea[name], select[name]').forEach(el => {
                        fields.push(el.name);
                    });
                    document.querySelectorAll('.o_field_widget[data-field]').forEach(el => {
                        fields.push(el.dataset.field);
                    });
                    document.querySelectorAll('.o_field_many2one[data-field]').forEach(el => {
                        fields.push(el.dataset.field + ' (many2one)');
                    });
                    return [...new Set(fields)].sort();
                }
            """)
            raise TimeoutError(
                f"Field '{field_name}' not found or not visible. Available fields: {available_fields}"
            )

        await field.scroll_into_view_if_needed()

        tag = await field.evaluate("el => el.tagName.toLowerCase()")
        input_type = await field.get_attribute("type") or ""
        field_class = await field.get_attribute("class") or ""

        # Check if this is a many2one field by looking at parent containers
        is_many2one = "many2one" in field_class.lower()
        if not is_many2one:
            is_many2one = await field.evaluate("""el => {
                let p = el.parentElement;
                while(p) {
                    if(p.className.includes('many2one')) return true;
                    p = p.parentElement;
                }
                return false;
            }""")

        if tag == "select":
            await field.select_option(label=str(value))
        elif input_type == "checkbox":
            current = await field.is_checked()
            if current != bool(value):
                await field.click()
        elif "datepicker" in field_class.lower() or input_type == "date":
            await field.fill(str(value))
            await self.page.keyboard.press("Enter")
        elif is_many2one:
            await self.fill_many2one(field_name, str(value))
        else:
            await field.click()
            await field.fill("")
            await field.fill(str(value))

        await self.wait.for_ajax()

    async def fill_many2one(
        self,
        field_name: str,
        value: str,
        create_if_not_found: bool = False,
        search_more: bool = False,
    ) -> None:
        field = self.get_field(field_name)
        await field.click()

        input_elem = field.locator("input").first
        await input_elem.fill(value)

        try:
            await self.page.wait_for_selector(
                ".o_dropdown_menu, .ui-autocomplete",
                timeout=5000
            )
        except Exception:
            raise TimeoutError(f"No dropdown found for many2one field '{field_name}'")

        if search_more:
            await self.page.get_by_text("Search More...").click()
            await self.wait.for_all()
            await self.page.locator(".o_list_view").get_by_text(value, exact=True).first.click()
        elif create_if_not_found:
            await self.page.get_by_text("Create and Edit...").click()
            await self.wait.for_all()
        else:
            dropdown_selector = ".o_dropdown_menu:visible, .ui-autocomplete:visible"
            dropdown_item = self.page.locator(dropdown_selector).get_by_text(value, exact=True).first
            if await dropdown_item.count() > 0:
                await dropdown_item.click()
            else:
                await self.page.keyboard.press("Enter")

        await self.wait.for_all()

    async def clear_field(self, field_name: str) -> None:
        field = self.get_field(field_name)

        clear_btn = field.locator(".o_field_widget_clear, .o_clear_button, [title='Clear']")
        if await clear_btn.count() > 0:
            await clear_btn.click()
        else:
            await field.fill("")

        await self.wait.for_ajax()

    async def go_to_tab(self, tab_name: str) -> None:
        tab = self.page.locator(
            ".o_notebook .nav-link, .o_notebook_tabs .nav-link, .nav-tabs .nav-link"
        ).get_by_text(tab_name, exact=True)
        await tab.click()
        await self.wait.for_ajax()

    async def search(self, query: str, clear_previous: bool = True) -> None:
        if clear_previous:
            await self.clear_search()

        search_btn = self.page.locator(".o_searchview_toggle, .o_searchview button")
        if await search_btn.count() > 0:
            await search_btn.click()

        search_input = self.page.locator(self.selectors.get("search_input"))
        await search_input.wait_for(state="visible", timeout=5000)
        await search_input.click()
        await search_input.fill(query)
        await self.page.keyboard.press("Enter")
        await self.wait.for_all()

    async def clear_search(self) -> None:
        clear_btn = self.page.locator(self.selectors.get("search_clear"))
        if await clear_btn.count() > 0:
            await clear_btn.click()
            await self.wait.for_ajax()

    async def filter_by(self, filter_name: str) -> None:
        await self.page.locator("button:has-text('Filters'), .o_filters_menu").click()
        await self.page.get_by_text(filter_name, exact=True).click()
        await self.wait.for_all()

    async def group_by(self, field_name: str) -> None:
        await self.page.locator("button:has-text('Group By'), .o_group_by_menu").click()
        await self.page.get_by_text(field_name, exact=True).click()
        await self.wait.for_all()

    def get_list_rows(self) -> Locator:
        return self.page.locator(self.selectors.get("list_row"))

    async def get_list_row_count(self) -> int:
        return await self.get_list_rows().count()

    async def click_list_row(self, row_index: int = 0) -> None:
        await self.get_list_rows().nth(row_index).click()
        await self.wait.for_all()

    async def click_list_row_by_value(self, column: str, value: str) -> None:
        cell = self.page.locator(
            f".o_data_row:has(td[data-field='{column}']:has-text('{value}'))"
        ).first
        await cell.click()
        await self.wait.for_all()

    async def select_list_rows(self, column: str, value: str) -> None:
        checkboxes = self.page.locator(
            f".o_data_row:has(td[data-field='{column}']:has-text('{value}')) "
            f".o_list_record_selector input, input[type='checkbox']"
        )
        await checkboxes.click()
        await self.wait.for_ajax()

    async def select_all_rows(self) -> None:
        await self.page.locator(
            ".o_list_view thead .o_list_record_selector input, "
            "thead input[type='checkbox']"
        ).click()
        await self.wait.for_ajax()

    async def get_list_values(self, columns: Optional[list[str]] = None) -> list[dict[str, str]]:
        rows = self.get_list_rows()
        result = []

        count = await rows.count()
        for i in range(count):
            row = rows.nth(i)
            row_data = {}

            if columns:
                for col in columns:
                    cell = row.locator(f"td[data-field='{col}']")
                    row_data[col] = await cell.inner_text() if await cell.count() > 0 else ""
            else:
                cells = row.locator("td.o_data_cell")
                cell_count = await cells.count()
                for j in range(cell_count):
                    cell = cells.nth(j)
                    field_name = await cell.get_attribute("data-field") or f"col_{j}"
                    row_data[field_name] = await cell.inner_text()

            result.append(row_data)

        return result

    async def pager_next(self) -> bool:
        next_btn = self.page.locator(self.selectors.get("pager_next"))
        if await next_btn.is_disabled():
            return False
        await next_btn.click()
        await self.wait.for_all()
        return True

    async def pager_previous(self) -> bool:
        prev_btn = self.page.locator(self.selectors.get("pager_prev"))
        if await prev_btn.is_disabled():
            return False
        await prev_btn.click()
        await self.wait.for_all()
        return True

    async def get_pager_info(self) -> dict[str, int]:
        info_elem = self.page.locator(self.selectors.get("pager_info"))
        text = await info_elem.inner_text()

        match = re.search(r"(\d+)-(\d+)\s*(?:of|/)\s*(\d+)", text)
        if match:
            return {
                "from": int(match.group(1)),
                "to": int(match.group(2)),
                "total": int(match.group(3)),
            }
        return {"from": 0, "to": 0, "total": 0}

    async def open_kanban_card(self, card_index: int = 0) -> None:
        await self.page.locator(self.selectors.get("kanban_card")).nth(card_index).click()
        await self.wait.for_all()

    def get_kanban_cards(self) -> Locator:
        return self.page.locator(self.selectors.get("kanban_card"))

    async def get_kanban_card_count(self) -> int:
        return await self.get_kanban_cards().count()

    async def is_modal_open(self) -> bool:
        return await self.page.locator(self.selectors.get("modal")).count() > 0

    async def close_modal(self, save: bool = False) -> None:
        modal = self.page.locator(self.selectors.get("modal"))

        if save:
            save_btn = modal.locator(
                "button[name='save'], button.btn-primary:has-text('Save'), "
                ".modal-footer button:last-child"
            ).first
            if await save_btn.count() > 0:
                await save_btn.click()
        else:
            cancel_btn = modal.locator(
                "button[name='cancel'], button.btn-secondary:has-text('Cancel'), "
                ".modal-footer button:first-child, .close"
            ).first
            if await cancel_btn.count() > 0:
                await cancel_btn.click()

        await self.wait.for_all()

    async def confirm_dialog(self) -> None:
        await self.page.get_by_role("button", name="OK").click()
        await self.wait.for_all()

    async def cancel_dialog(self) -> None:
        await self.page.get_by_role("button", name="Cancel").click()
        await self.wait.for_all()

    async def get_notification(self) -> Optional[dict[str, str]]:
        notif = self.page.locator(self.selectors.get("notification")).first
        if await notif.count() == 0:
            return None

        classes = await notif.get_attribute("class") or ""
        if "success" in classes:
            notification_type = "success"
        elif "danger" in classes or "error" in classes:
            notification_type = "error"
        elif "warning" in classes:
            notification_type = "warning"
        else:
            notification_type = "info"

        return {
            "type": notification_type,
            "message": await notif.inner_text(),
        }

    async def wait_for_notification(self, timeout: int = 5000) -> Optional[dict[str, str]]:
        await self.page.wait_for_selector(self.selectors.get("notification"), timeout=timeout)
        return await self.get_notification()

    async def dismiss_notification(self) -> None:
        close_btn = self.page.locator(f"{self.selectors.get('notification')} .close, .toast-close")
        if await close_btn.count() > 0:
            await close_btn.click()

    async def take_screenshot(self, path: str) -> None:
        await self.page.screenshot(path=path)

    async def wait_for_url_contains(self, text: str, timeout: int = 10000) -> None:
        await self.page.wait_for_url(f"**/*{text}*", timeout=timeout)

    @asynccontextmanager
    async def expect_ajax(self, timeout: int = 30000) -> AsyncGenerator[None, None]:
        yield
        await self.wait.for_all()

    async def execute_js(self, script: str, *args: Any) -> Any:
        return await self.page.evaluate(script, *args)

    async def get_odoo_version(self) -> Optional[str]:
        return await self.execute_js("typeof odoo !== 'undefined' ? odoo.version_info : null")

    async def install_module(self, module_name: str, upgrade: bool = False) -> bool:
        await self.go_to_app("Apps")
        await self.search(f"module:{module_name}")

        card = self.page.locator(f".o_kanban_record:has-text('{module_name}')").first
        if await card.count() == 0:
            return False

        status_elem = card.locator(".o_module_status")
        status = await status_elem.inner_text() if await status_elem.count() > 0 else ""

        if "Installed" in status and not upgrade:
            return True

        await card.click()

        install_btn = self.page.get_by_role("button", name="Install")
        if await install_btn.count() > 0:
            await install_btn.click()
            await self.wait.for_all(timeout=120000)
            return True

        return False

    def page(self, name: str):
        from odoo_playwright.page_async import AsyncOdooPage
        return AsyncOdooPage(self, name)

    def view(self, model: str, view_type: str = "form"):
        from odoo_playwright.views_async import AsyncFormView, AsyncKanbanView, AsyncListView

        view_classes = {
            "form": AsyncFormView,
            "list": AsyncListView,
            "tree": AsyncListView,
            "kanban": AsyncKanbanView,
        }

        view_class = view_classes.get(view_type, AsyncFormView)
        return view_class(self, model)
