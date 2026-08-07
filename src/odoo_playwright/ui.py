"""Core Odoo UI interaction class using Playwright."""

import re
import urllib.parse
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

from playwright.sync_api import Locator, Page

from odoo_playwright.selectors import get_selectors
from odoo_playwright.wait import WaitHelper


class OdooUI:
    """Main class for interacting with Odoo UI using Playwright."""

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
        self.wait = WaitHelper(page)
        self._current_model: Optional[str] = None

    def url(self, path: str = "") -> str:
        """Build complete URL from path."""
        return f"{self.base_url}/{path.lstrip('/')}"

    def navigate(self, path: str = "") -> None:
        """Navigate to a specific path."""
        self.page.goto(self.url(path))
        self.wait.for_all()

    def login(
        self,
        username: str,
        password: str,
        database: Optional[str] = None,
    ) -> None:
        """Login to Odoo."""
        self.page.goto(self.url("/web"))

        db_selector = self.page.locator("#db, select[name='db']")
        if db_selector.count() > 0 and database:
            db_selector.select_option(database)
        elif db_selector.count() > 0:
            db_selector.first.click()
            self.page.keyboard.press("ArrowDown")
            self.page.keyboard.press("Tab")

        self.page.locator("#login").fill(username)
        self.page.locator("#password").fill(password)
        self.page.locator("button[type='submit'], .btn-primary").click()

        self.wait.for_all()
        self.page.wait_for_url("**/web**")

    def logout(self) -> None:
        """Logout from Odoo."""
        self.page.locator(".o_user_menu, .oe_topbar_name").click()
        self.page.get_by_text("Log out", exact=True).click()
        self.wait.for_all()

    def get_url_fragments(self) -> dict[str, str]:
        """Parse URL hash/fragment into dictionary."""
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

    def get_current_model(self) -> Optional[str]:
        """Get the current model from URL or page."""
        fragments = self.get_url_fragments()
        if "model" in fragments:
            return fragments["model"]

        model_input = self.page.locator("input[name='model'], [data-model]")
        if model_input.count() > 0:
            return model_input.first.get_attribute("value") or model_input.first.get_attribute("data-model")

        return self._current_model

    def go_to_app(self, app_name: str, timeout: int = 10000) -> None:
        """Navigate to an app by clicking on its menu item."""
        self.wait.for_all()

        app_menu = self.page.get_by_text(app_name, exact=True).first
        app_menu.click()

        self.wait.for_all()
        self.page.wait_for_selector(".o_content, .o_view_controller", timeout=timeout)

    def go_to_menu(self, *menu_path: str, timeout: int = 10000) -> None:
        """Navigate through menu hierarchy.

        Example: ui.go_to_menu("Sales", "Orders", "Quotations")
        """
        if len(menu_path) == 0:
            return

        self.wait.for_all()

        menu_items = list(menu_path)
        first_item = menu_items.pop(0)

        self.page.get_by_text(first_item, exact=True).first.click()
        self.wait.for_all()

        for item in menu_items:
            menu_locator = self.page.locator(
                ".o_submenu, .oe_secondary_menu, .o_menu_entry_lvl_2, .o_menu_entry_lvl_3"
            ).get_by_text(item, exact=True).first
            menu_locator.click()
            self.wait.for_all()

        self.page.wait_for_selector(".o_content, .o_view_controller", timeout=timeout)

    def switch_view(self, view_type: str) -> None:
        """Switch to list, form, kanban, calendar, graph, etc."""
        view_button = self.page.locator(
            f"[data-view-type='{view_type}'], button[title*='{view_type}'], .o_cp_switch_buttons button[data-view-type='{view_type}']"
        )
        view_button.click()
        self.wait.for_all()

    def get_current_view_type(self) -> Optional[str]:
        """Get the current view type (form, list, kanban, etc.)."""
        fragments = self.get_url_fragments()
        return fragments.get("view_type")

    def click_create(self, timeout: int = 10000) -> None:
        """Click the Create button."""
        create_btn = self.page.locator(self.selectors.get("button_create"))
        create_btn.click()
        self.wait.for_all()

    def click_save(self, timeout: int = 10000) -> None:
        """Click the Save button."""
        save_btn = self.page.locator(self.selectors.get("button_save"))
        save_btn.click()
        self.wait.for_all()

    def click_edit(self, timeout: int = 10000) -> None:
        """Click the Edit button."""
        edit_btn = self.page.locator(self.selectors.get("button_edit"))
        edit_btn.click()
        self.wait.for_all()

    def click_discard(self, timeout: int = 10000) -> None:
        """Click the Discard button."""
        discard_btn = self.page.locator(self.selectors.get("button_discard"))
        discard_btn.click()
        self.wait.for_all()

    def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
        """Click Delete and optionally confirm."""
        delete_btn = self.page.locator(self.selectors.get("button_delete"))
        delete_btn.click()

        if confirm:
            self.page.on("dialog", lambda dialog: dialog.accept())
            self.wait.for_all()

    def click_action(self, action_name: str) -> None:
        """Click an action button by name."""
        self.page.locator(self.selectors.get("button_action")).click()
        self.page.get_by_text(action_name, exact=True).click()
        self.wait.for_all()

    def click_button(self, button_name: str, by_aria_label: bool = False) -> None:
        """Click a button by its text or aria-label."""
        if by_aria_label:
            self.page.get_by_role("button", name=button_name).click()
        else:
            self.page.get_by_role("button", name=button_name, exact=True).click()
        self.wait.for_all()

    def get_field(self, field_name: str) -> Locator:
        """Get a field locator by name."""
        return self.page.locator(
            f"[name='{field_name}'], [data-field='{field_name}'], [data-field-name='{field_name}']"
        ).first

    def get_field_value(self, field_name: str) -> str:
        """Get the value of a field."""
        field = self.get_field(field_name)

        tag = field.evaluate("el => el.tagName.toLowerCase()")
        input_type = field.get_attribute("type") or ""

        if tag == "select":
            return field.locator("option:checked").inner_text()
        elif input_type == "checkbox":
            return str(field.is_checked())
        elif tag == "input" or tag == "textarea":
            return field.input_value()
        else:
            return field.inner_text()

    def fill_field(self, field_name: str, value: Any) -> None:
        """Fill a field with a value."""
        field = self.get_field(field_name)

        field.wait_for(state="visible")
        field.scroll_into_view_if_needed()

        tag = field.evaluate("el => el.tagName.toLowerCase()")
        input_type = field.get_attribute("type") or ""
        field_class = field.get_attribute("class") or ""

        if tag == "select":
            field.select_option(label=str(value))
        elif input_type == "checkbox":
            current = field.is_checked()
            if current != bool(value):
                field.click()
        elif "datepicker" in field_class.lower() or input_type == "date":
            field.fill(str(value))
            self.page.keyboard.press("Enter")
        elif "many2one" in field_class.lower():
            self.fill_many2one(field_name, str(value))
        else:
            field.click()
            field.fill("")
            field.fill(str(value))

        self.wait.for_ajax()

    def fill_many2one(
        self,
        field_name: str,
        value: str,
        create_if_not_found: bool = False,
        search_more: bool = False,
    ) -> None:
        """Fill a many2one field."""
        field = self.get_field(field_name)
        field.click()

        input_elem = field.locator("input").first
        input_elem.fill(value)

        self.page.wait_for_selector(".ui-autocomplete, .o_dropdown_menu", timeout=5000)

        if search_more:
            self.page.get_by_text("Search More...").click()
            self.wait.for_all()
            self.page.locator(".o_list_view").get_by_text(value, exact=True).first.click()
        elif create_if_not_found:
            self.page.get_by_text("Create and Edit...").click()
            self.wait.for_all()
        else:
            dropdown_item = self.page.locator(".ui-autocomplete, .o_dropdown_menu").get_by_text(value, exact=True).first
            if dropdown_item.count() > 0:
                dropdown_item.click()
            else:
                self.page.keyboard.press("Enter")

        self.wait.for_all()

    def clear_field(self, field_name: str) -> None:
        """Clear a field."""
        field = self.get_field(field_name)

        clear_btn = field.locator(".o_field_widget_clear, .o_clear_button, [title='Clear']")
        if clear_btn.count() > 0:
            clear_btn.click()
        else:
            field.fill("")

        self.wait.for_ajax()

    def go_to_tab(self, tab_name: str) -> None:
        """Click on a tab in a form view."""
        tab = self.page.locator(".o_notebook_tabs, .nav-tabs").get_by_role("tab", name=tab_name)
        tab.click()
        self.wait.for_ajax()

    def search(self, query: str, clear_previous: bool = True) -> None:
        """Search in the current view."""
        if clear_previous:
            self.clear_search()

        search_input = self.page.locator(self.selectors.get("search_input"))
        search_input.click()
        search_input.fill(query)
        self.page.keyboard.press("Enter")
        self.wait.for_all()

    def clear_search(self) -> None:
        """Clear all search facets."""
        clear_btn = self.page.locator(self.selectors.get("search_clear"))
        if clear_btn.count() > 0:
            clear_btn.click()
            self.wait.for_ajax()

    def filter_by(self, filter_name: str) -> None:
        """Apply a filter from the filter dropdown."""
        self.page.locator("button:has-text('Filters'), .o_filters_menu").click()
        self.page.get_by_text(filter_name, exact=True).click()
        self.wait.for_all()

    def group_by(self, field_name: str) -> None:
        """Group by a field."""
        self.page.locator("button:has-text('Group By'), .o_group_by_menu").click()
        self.page.get_by_text(field_name, exact=True).click()
        self.wait.for_all()

    def get_list_rows(self) -> Locator:
        """Get all rows in list view."""
        return self.page.locator(self.selectors.get("list_row"))

    def get_list_row_count(self) -> int:
        """Count rows in list view."""
        return self.get_list_rows().count()

    def click_list_row(self, row_index: int = 0) -> None:
        """Click a row in list view by index."""
        self.get_list_rows().nth(row_index).click()
        self.wait.for_all()

    def click_list_row_by_value(self, column: str, value: str) -> None:
        """Click a row where a column has a specific value."""
        cell = self.page.locator(
            f".o_data_row:has(td[data-field='{column}']:has-text('{value}'))"
        ).first
        cell.click()
        self.wait.for_all()

    def select_list_rows(self, column: str, value: str) -> None:
        """Select rows where a column has a specific value."""
        checkboxes = self.page.locator(
            f".o_data_row:has(td[data-field='{column}']:has-text('{value}')) "
            f".o_list_record_selector input, input[type='checkbox']"
        )
        checkboxes.click()
        self.wait.for_ajax()

    def select_all_rows(self) -> None:
        """Select all rows in list view."""
        self.page.locator(
            ".o_list_view thead .o_list_record_selector input, "
            "thead input[type='checkbox']"
        ).click()
        self.wait.for_ajax()

    def get_list_values(self, columns: Optional[list[str]] = None) -> list[dict[str, str]]:
        """Get all row values from list view."""
        rows = self.get_list_rows()
        result = []

        for i in range(rows.count()):
            row = rows.nth(i)
            row_data = {}

            if columns:
                for col in columns:
                    cell = row.locator(f"td[data-field='{col}']")
                    row_data[col] = cell.inner_text() if cell.count() > 0 else ""
            else:
                cells = row.locator("td.o_data_cell")
                for j in range(cells.count()):
                    cell = cells.nth(j)
                    field_name = cell.get_attribute("data-field") or f"col_{j}"
                    row_data[field_name] = cell.inner_text()

            result.append(row_data)

        return result

    def pager_next(self) -> bool:
        """Go to next page. Returns True if successful."""
        next_btn = self.page.locator(self.selectors.get("pager_next"))
        if next_btn.is_disabled():
            return False
        next_btn.click()
        self.wait.for_all()
        return True

    def pager_previous(self) -> bool:
        """Go to previous page. Returns True if successful."""
        prev_btn = self.page.locator(self.selectors.get("pager_prev"))
        if prev_btn.is_disabled():
            return False
        prev_btn.click()
        self.wait.for_all()
        return True

    def pager_first(self) -> None:
        """Go to first page."""
        self.page.locator(self.selectors.get("pager_prev")).click()
        self.wait.for_all()

    def pager_last(self) -> None:
        """Go to last page."""
        self.page.locator(self.selectors.get("pager_next")).click()
        self.wait.for_all()

    def get_pager_info(self) -> dict[str, int]:
        """Get pager information (from, to, total)."""
        info_elem = self.page.locator(self.selectors.get("pager_info"))
        text = info_elem.inner_text()

        match = re.search(r"(\d+)-(\d+)\s*(?:of|/)\s*(\d+)", text)
        if match:
            return {
                "from": int(match.group(1)),
                "to": int(match.group(2)),
                "total": int(match.group(3)),
            }
        return {"from": 0, "to": 0, "total": 0}

    def open_kanban_card(self, card_index: int = 0) -> None:
        """Open a kanban card."""
        self.page.locator(self.selectors.get("kanban_card")).nth(card_index).click()
        self.wait.for_all()

    def get_kanban_cards(self) -> Locator:
        """Get all kanban cards."""
        return self.page.locator(self.selectors.get("kanban_card"))

    def get_kanban_card_count(self) -> int:
        """Count kanban cards."""
        return self.get_kanban_cards().count()

    def is_modal_open(self) -> bool:
        """Check if a modal dialog is open."""
        return self.page.locator(self.selectors.get("modal")).count() > 0

    def close_modal(self, save: bool = False) -> None:
        """Close the current modal dialog."""
        modal = self.page.locator(self.selectors.get("modal"))

        if save:
            modal.locator("button[name='save'], button:has-text('Save'), .btn-primary").click()
        else:
            modal.locator("button[name='cancel'], button:has-text('Cancel'), .btn-secondary, .close").first.click()

        self.wait.for_all()

    def confirm_dialog(self) -> None:
        """Accept a confirmation dialog."""
        self.page.get_by_role("button", name="OK").click()
        self.wait.for_all()

    def cancel_dialog(self) -> None:
        """Cancel a dialog."""
        self.page.get_by_role("button", name="Cancel").click()
        self.wait.for_all()

    def get_notification(self) -> Optional[dict[str, str]]:
        """Get the current notification (if any)."""
        notif = self.page.locator(self.selectors.get("notification")).first
        if notif.count() == 0:
            return None

        classes = notif.get_attribute("class") or ""
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
            "message": notif.inner_text(),
        }

    def wait_for_notification(self, timeout: int = 5000) -> Optional[dict[str, str]]:
        """Wait for a notification to appear."""
        self.page.wait_for_selector(self.selectors.get("notification"), timeout=timeout)
        return self.get_notification()

    def dismiss_notification(self) -> None:
        """Dismiss any visible notification."""
        close_btn = self.page.locator(f"{self.selectors.get('notification')} .close, .toast-close")
        if close_btn.count() > 0:
            close_btn.click()

    def take_screenshot(self, path: str) -> None:
        """Take a screenshot."""
        self.page.screenshot(path=path)

    def wait_for_url_contains(self, text: str, timeout: int = 10000) -> None:
        """Wait for URL to contain specific text."""
        self.page.wait_for_url(f"**/*{text}*", timeout=timeout)

    @contextmanager
    def expect_ajax(self, timeout: int = 30000) -> Generator[None, None, None]:
        """Context manager to wait for AJAX after an operation."""
        yield
        self.wait.for_all()

    def execute_js(self, script: str, *args: Any) -> Any:
        """Execute JavaScript in the page."""
        return self.page.evaluate(script, *args)

    def get_odoo_version(self) -> Optional[str]:
        """Get Odoo version from JavaScript."""
        return self.execute_js("typeof odoo !== 'undefined' ? odoo.version_info : null")

    def install_module(self, module_name: str, upgrade: bool = False) -> bool:
        """Install or upgrade a module."""
        self.go_to_app("Apps")
        self.search(f"module:{module_name}")

        card = self.page.locator(f".o_kanban_record:has-text('{module_name}')").first
        if card.count() == 0:
            return False

        status = card.locator(".o_module_status").inner_text() if card.locator(".o_module_status").count() > 0 else ""

        if "Installed" in status and not upgrade:
            return True

        card.click()

        install_btn = self.page.get_by_role("button", name="Install")
        if install_btn.count() > 0:
            install_btn.click()
            self.wait.for_all(timeout=120000)
            return True

        return False

    def page(self, name: str):
        """Get a page object for an app."""
        from odoo_playwright.page import OdooPage
        return OdooPage(self, name)

    def view(self, model: str, view_type: str = "form"):
        """Get a view object."""
        from odoo_playwright.views import FormView, KanbanView, ListView

        view_classes = {
            "form": FormView,
            "list": ListView,
            "tree": ListView,
            "kanban": KanbanView,
        }

        view_class = view_classes.get(view_type, FormView)
        return view_class(self, model)
