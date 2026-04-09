"""Async view objects for Odoo UI (Form, List, Kanban)."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from playwright.async_api import Locator, Page

if TYPE_CHECKING:
    from odoo_playwright.ui_async import AsyncOdooUI


class AsyncBaseView:
    """Async base class for all Odoo views."""

    def __init__(self, ui: "AsyncOdooUI", model: str):
        self.ui = ui
        self.page = ui.page
        self.model = model
        self.selectors = ui.selectors

    def get_field(self, field_name: str) -> Locator:
        """Get a field element by name."""
        return self.page.locator(
            f"[name='{field_name}'], [data-field='{field_name}'], [data-field-name='{field_name}']"
        ).first

    async def get_field_value(self, field_name: str) -> str:
        """Get the value of a field."""
        return await self.ui.get_field_value(field_name)

    async def fill_field(self, field_name: str, value: Any) -> None:
        """Fill a field with a value."""
        await self.ui.fill_field(field_name, value)

    async def fill(self, **fields: Any) -> None:
        """Fill multiple fields at once."""
        for field_name, value in fields.items():
            await self.fill_field(field_name, value)

    async def click_button(self, button_name: str) -> None:
        """Click a button by name."""
        await self.ui.click_button(button_name)

    async def wait_for_load(self, timeout: int = 30000) -> None:
        """Wait for the view to finish loading."""
        await self.ui.wait.for_all()


class AsyncFormView(AsyncBaseView):
    """Async form view helper class."""

    async def create(self, **fields: Any) -> None:
        """Click create, fill fields, and save."""
        await self.ui.click_create()
        await self.fill(**fields)
        await self.save()

    async def edit(self) -> None:
        """Click the edit button."""
        await self.ui.click_edit()

    async def save(self) -> None:
        """Click the save button."""
        await self.ui.click_save()

    async def discard(self) -> None:
        """Click the discard button."""
        await self.ui.click_discard()

    async def delete(self, confirm: bool = True) -> None:
        """Delete the current record."""
        await self.ui.click_delete(confirm=confirm)

    async def go_to_tab(self, tab_name: str) -> None:
        """Navigate to a tab in the form."""
        await self.ui.go_to_tab(tab_name)

    async def get_status(self) -> str:
        """Get the status bar value."""
        status = self.page.locator(".o_statusbar_status .o_status_active, .o_statusbar_status button.active")
        if await status.count() > 0:
            return await status.inner_text()
        return ""

    async def set_status(self, status_name: str) -> None:
        """Set status by clicking a status button."""
        status_btn = self.page.locator(
            f".o_statusbar_buttons button:has-text('{status_name}'), "
            f".o_statusbar_status button:has-text('{status_name}')"
        )
        await status_btn.click()
        await self.ui.wait.for_all()

    async def is_readonly(self) -> bool:
        """Check if form is in readonly mode."""
        return await self.page.locator(".o_form_readonly").count() > 0

    async def is_dirty(self) -> bool:
        """Check if form has unsaved changes."""
        return await self.page.locator(".o_form_dirty, [data-dirty='true']").count() > 0

    async def add_one2many_item(self, field_name: str) -> "AsyncFormView":
        """Add an item to a one2many field."""
        add_btn = self.page.locator(
            f"[name='{field_name}'] .o_field_widget_add, "
            f"[data-field='{field_name}'] .o_form_field_one2many_list_row_add a, "
            f"[name='{field_name}'] .o_add_item"
        )
        await add_btn.click()
        await self.ui.wait.for_ajax()
        return self

    async def remove_one2many_item(self, field_name: str, row_index: int = 0) -> None:
        """Remove an item from a one2many field."""
        delete_btn = self.page.locator(
            f"[name='{field_name}'] .o_data_row:nth-child({row_index + 1}) "
            f".o_list_record_delete, "
            f"[data-field='{field_name}'] .o_data_row:nth-child({row_index + 1}) [title='Delete']"
        )
        await delete_btn.click()
        await self.ui.wait.for_ajax()

    async def get_one2many_values(self, field_name: str, columns: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Get all values from a one2many field."""
        result = []
        rows = self.page.locator(f"[name='{field_name}'] .o_data_row, [data-field='{field_name}'] .o_data_row")

        count = await rows.count()
        for i in range(count):
            row = rows.nth(i)
            row_data = {}

            if columns:
                for col in columns:
                    cell = row.locator(f"td[data-field='{col}'], td[name='{col}']")
                    row_data[col] = await cell.inner_text() if await cell.count() > 0 else ""
            else:
                cells = row.locator("td.o_data_cell")
                cell_count = await cells.count()
                for j in range(cell_count):
                    cell = cells.nth(j)
                    field = await cell.get_attribute("data-field") or f"col_{j}"
                    row_data[field] = await cell.inner_text()

            result.append(row_data)

        return result

    async def upload_file(self, field_name: str, file_path: str) -> None:
        """Upload a file to a binary field."""
        file_input = self.page.locator(
            f"[name='{field_name}'] input[type='file'], "
            f"[data-field='{field_name}'] input[type='file']"
        )
        await file_input.set_input_files(file_path)
        await self.ui.wait.for_all()

    async def clear_file(self, field_name: str) -> None:
        """Clear a binary field."""
        clear_btn = self.page.locator(
            f"[name='{field_name}'] .o_clear_file_button, "
            f"[data-field='{field_name}'] .fa-trash-o"
        )
        await clear_btn.click()
        await self.ui.wait.for_ajax()

    async def open_translations(self, field_name: str) -> None:
        """Open translation dialog for a field."""
        translate_btn = self.page.locator(
            f"[name='{field_name}'] ~ .o_field_translate, "
            f"[data-field='{field_name}'] ~ .oe_field_translate"
        )
        await translate_btn.click()
        await self.ui.wait.for_all()


class AsyncListView(AsyncBaseView):
    """Async list/tree view helper class."""

    async def create(self, **fields: Any) -> None:
        """Click create and fill the form (opens form view)."""
        await self.ui.click_create()
        form = AsyncFormView(self.ui, self.model)
        await form.fill(**fields)
        await form.save()

    async def get_row_count(self) -> int:
        """Get the total number of rows."""
        return await self.ui.get_list_row_count()

    def get_rows(self) -> Locator:
        """Get all rows."""
        return self.ui.get_list_rows()

    async def get_values(self, columns: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Get all row values."""
        return await self.ui.get_list_values(columns)

    async def click_row(self, row_index: int = 0) -> AsyncFormView:
        """Click a row to open the form view."""
        await self.ui.click_list_row(row_index)
        return AsyncFormView(self.ui, self.model)

    async def click_row_by_value(self, column: str, value: str) -> AsyncFormView:
        """Click a row where a column has a specific value."""
        await self.ui.click_list_row_by_value(column, value)
        return AsyncFormView(self.ui, self.model)

    async def select_row(self, row_index: int) -> None:
        """Select a row by index."""
        checkbox = self.page.locator(
            f".o_data_row:nth-child({row_index + 1}) .o_list_record_selector input, "
            f".o_data_row:nth-child({row_index + 1}) input[type='checkbox']"
        )
        await checkbox.click()
        await self.ui.wait.for_ajax()

    async def select_rows_by_value(self, column: str, value: str) -> None:
        """Select rows where a column has a specific value."""
        await self.ui.select_list_rows(column, value)

    async def select_all(self) -> None:
        """Select all rows."""
        await self.ui.select_all_rows()

    async def delete_selected(self) -> None:
        """Delete selected rows."""
        await self.ui.click_action("Delete")
        await self.ui.confirm_dialog()

    async def pager_next(self) -> bool:
        """Go to next page."""
        return await self.ui.pager_next()

    async def pager_previous(self) -> bool:
        """Go to previous page."""
        return await self.ui.pager_previous()

    async def get_pager_info(self) -> Dict[str, int]:
        """Get pager information."""
        return await self.ui.get_pager_info()

    async def search(self, query: str, clear_previous: bool = True) -> None:
        """Search in the list view."""
        await self.ui.search(query, clear_previous)

    async def filter_by(self, filter_name: str) -> None:
        """Apply a filter."""
        await self.ui.filter_by(filter_name)

    async def group_by(self, field_name: str) -> None:
        """Group by a field."""
        await self.ui.group_by(field_name)

    async def is_empty(self) -> bool:
        """Check if the list is empty."""
        return await self.page.locator(".o_nocontent_help, .oe_nocontent").count() > 0

    async def sort_by(self, column: str) -> None:
        """Sort by a column."""
        header = self.page.locator(f"th[data-field='{column}'], th[name='{column}']")
        await header.click()
        await self.ui.wait.for_ajax()


class AsyncKanbanView(AsyncBaseView):
    """Async kanban view helper class."""

    async def create(self, **fields: Any) -> None:
        """Click create and fill the form."""
        await self.ui.click_create()
        form = AsyncFormView(self.ui, self.model)
        await form.fill(**fields)
        await form.save()

    async def get_card_count(self) -> int:
        """Get the total number of cards."""
        return await self.ui.get_kanban_card_count()

    def get_cards(self) -> Locator:
        """Get all kanban cards."""
        return self.ui.get_kanban_cards()

    async def open_card(self, card_index: int = 0) -> AsyncFormView:
        """Open a kanban card."""
        await self.ui.open_kanban_card(card_index)
        return AsyncFormView(self.ui, self.model)

    async def get_column_count(self) -> int:
        """Get the number of columns."""
        return await self.page.locator(self.selectors.get("kanban_column")).count()

    def get_column_cards(self, column_name: str) -> Locator:
        """Get cards in a specific column."""
        return self.page.locator(
            f".o_kanban_group:has(.o_column_title:has-text('{column_name}')) .o_kanban_record"
        )

    async def move_card_to_column(self, card_title: str, column_name: str) -> None:
        """Drag and drop a card to another column."""
        card = self.page.locator(f".o_kanban_record:has-text('{card_title}')").first
        column = self.page.locator(f".o_kanban_group:has(.o_column_title:has-text('{column_name}'))")

        await card.drag_to(column)
        await self.ui.wait.for_ajax()

    async def quick_create(self, column_name: Optional[str] = None, **fields: Any) -> None:
        """Create a card using quick create in a column."""
        if column_name:
            column = self.page.locator(
                f".o_kanban_group:has(.o_column_title:has-text('{column_name}'))"
            )
            add_btn = column.locator(".o_kanban_quick_add")
            await add_btn.click()
        else:
            await self.page.locator(".o_kanban_quick_add").first.click()

        await self.ui.wait.for_ajax()

        for field_name, value in fields.items():
            input_field = self.page.locator(f".o_kanban_quick_create [name='{field_name}']")
            if await input_field.count() > 0:
                await input_field.fill(str(value))

        await self.page.locator(".o_kanban_quick_create button[type='submit'], .o_kanban_quick_create .btn-primary").click()
        await self.ui.wait.for_all()

    async def search(self, query: str, clear_previous: bool = True) -> None:
        """Search in the kanban view."""
        await self.ui.search(query, clear_previous)

    async def filter_by(self, filter_name: str) -> None:
        """Apply a filter."""
        await self.ui.filter_by(filter_name)

    async def group_by(self, field_name: str) -> None:
        """Group by a field."""
        await self.ui.group_by(field_name)
