"""View objects for Odoo UI (Form, List, Kanban)."""

from typing import TYPE_CHECKING, Any, Optional

from playwright.sync_api import Locator

if TYPE_CHECKING:
    from odoo_playwright.ui import OdooUI


class BaseView:
    """Base class for all Odoo views."""

    def __init__(self, ui: "OdooUI", model: str):
        self.ui = ui
        self.page = ui.page
        self.model = model
        self.selectors = ui.selectors

    def get_field(self, field_name: str) -> Locator:
        """Get a field element by name."""
        return self.page.locator(
            f"[name='{field_name}'], [data-field='{field_name}'], [data-field-name='{field_name}']"
        ).first

    def get_field_value(self, field_name: str) -> str:
        """Get the value of a field."""
        return self.ui.get_field_value(field_name)

    def fill_field(self, field_name: str, value: Any) -> None:
        """Fill a field with a value."""
        self.ui.fill_field(field_name, value)

    def fill(self, **fields: Any) -> None:
        """Fill multiple fields at once."""
        for field_name, value in fields.items():
            self.fill_field(field_name, value)

    def click_button(self, button_name: str) -> None:
        """Click a button by name."""
        self.ui.click_button(button_name)

    def wait_for_load(self, timeout: int = 30000) -> None:
        """Wait for the view to finish loading."""
        self.ui.wait.for_all()


class FormView(BaseView):
    """Form view helper class."""

    def create(self, **fields: Any) -> None:
        """Click create, fill fields, and save."""
        self.ui.click_create()
        self.fill(**fields)
        self.save()

    def edit(self) -> None:
        """Click the edit button."""
        self.ui.click_edit()

    def save(self) -> None:
        """Click the save button."""
        self.ui.click_save()

    def discard(self) -> None:
        """Click the discard button."""
        self.ui.click_discard()

    def delete(self, confirm: bool = True) -> None:
        """Delete the current record."""
        self.ui.click_delete(confirm=confirm)

    def go_to_tab(self, tab_name: str) -> None:
        """Navigate to a tab in the form."""
        self.ui.go_to_tab(tab_name)

    def get_status(self) -> str:
        """Get the status bar value."""
        status = self.page.locator(".o_statusbar_status .o_status_active, .o_statusbar_status button.active")
        if status.count() > 0:
            return status.inner_text()
        return ""

    def set_status(self, status_name: str) -> None:
        """Set status by clicking a status button."""
        status_btn = self.page.locator(
            f".o_statusbar_buttons button:has-text('{status_name}'), "
            f".o_statusbar_status button:has-text('{status_name}')"
        )
        status_btn.click()
        self.ui.wait.for_all()

    def is_readonly(self) -> bool:
        """Check if form is in readonly mode."""
        return self.page.locator(".o_form_readonly").count() > 0

    def is_dirty(self) -> bool:
        """Check if form has unsaved changes."""
        return self.page.locator(".o_form_dirty, [data-dirty='true']").count() > 0

    def add_one2many_item(self, field_name: str) -> "FormView":
        """Add an item to a one2many field."""
        add_btn = self.page.locator(
            f"[name='{field_name}'] .o_field_widget_add, "
            f"[data-field='{field_name}'] .o_form_field_one2many_list_row_add a, "
            f"[name='{field_name}'] .o_add_item"
        )
        add_btn.click()
        self.ui.wait.for_ajax()
        return self

    def remove_one2many_item(self, field_name: str, row_index: int = 0) -> None:
        """Remove an item from a one2many field."""
        delete_btn = self.page.locator(
            f"[name='{field_name}'] .o_data_row:nth-child({row_index + 1}) "
            f".o_list_record_delete, "
            f"[data-field='{field_name}'] .o_data_row:nth-child({row_index + 1}) [title='Delete']"
        )
        delete_btn.click()
        self.ui.wait.for_ajax()

    def get_one2many_values(self, field_name: str, columns: Optional[list[str]] = None) -> list[dict[str, str]]:
        """Get all values from a one2many field."""
        result = []
        rows = self.page.locator(f"[name='{field_name}'] .o_data_row, [data-field='{field_name}'] .o_data_row")

        for i in range(rows.count()):
            row = rows.nth(i)
            row_data = {}

            if columns:
                for col in columns:
                    cell = row.locator(f"td[data-field='{col}'], td[name='{col}']")
                    row_data[col] = cell.inner_text() if cell.count() > 0 else ""
            else:
                cells = row.locator("td.o_data_cell")
                for j in range(cells.count()):
                    cell = cells.nth(j)
                    field = cell.get_attribute("data-field") or f"col_{j}"
                    row_data[field] = cell.inner_text()

            result.append(row_data)

        return result

    def upload_file(self, field_name: str, file_path: str) -> None:
        """Upload a file to a binary field."""
        file_input = self.page.locator(
            f"[name='{field_name}'] input[type='file'], "
            f"[data-field='{field_name}'] input[type='file']"
        )
        file_input.set_input_files(file_path)
        self.ui.wait.for_all()

    def clear_file(self, field_name: str) -> None:
        """Clear a binary field."""
        clear_btn = self.page.locator(
            f"[name='{field_name}'] .o_clear_file_button, "
            f"[data-field='{field_name}'] .fa-trash-o"
        )
        clear_btn.click()
        self.ui.wait.for_ajax()

    def open_translations(self, field_name: str) -> None:
        """Open translation dialog for a field."""
        translate_btn = self.page.locator(
            f"[name='{field_name}'] ~ .o_field_translate, "
            f"[data-field='{field_name}'] ~ .oe_field_translate"
        )
        translate_btn.click()
        self.ui.wait.for_all()


class ListView(BaseView):
    """List/Tree view helper class."""

    def create(self, **fields: Any) -> None:
        """Click create and fill the form (opens form view)."""
        self.ui.click_create()
        form = FormView(self.ui, self.model)
        form.fill(**fields)
        form.save()

    def get_row_count(self) -> int:
        """Get the total number of rows."""
        return self.ui.get_list_row_count()

    def get_rows(self) -> Locator:
        """Get all rows."""
        return self.ui.get_list_rows()

    def get_values(self, columns: Optional[list[str]] = None) -> list[dict[str, str]]:
        """Get all row values."""
        return self.ui.get_list_values(columns)

    def click_row(self, row_index: int = 0) -> FormView:
        """Click a row to open the form view."""
        self.ui.click_list_row(row_index)
        return FormView(self.ui, self.model)

    def click_row_by_value(self, column: str, value: str) -> FormView:
        """Click a row where a column has a specific value."""
        self.ui.click_list_row_by_value(column, value)
        return FormView(self.ui, self.model)

    def select_row(self, row_index: int) -> None:
        """Select a row by index."""
        checkbox = self.page.locator(
            f".o_data_row:nth-child({row_index + 1}) .o_list_record_selector input, "
            f".o_data_row:nth-child({row_index + 1}) input[type='checkbox']"
        )
        checkbox.click()
        self.ui.wait.for_ajax()

    def select_rows_by_value(self, column: str, value: str) -> None:
        """Select rows where a column has a specific value."""
        self.ui.select_list_rows(column, value)

    def select_all(self) -> None:
        """Select all rows."""
        self.ui.select_all_rows()

    def delete_selected(self) -> None:
        """Delete selected rows."""
        self.ui.click_action("Delete")
        self.ui.confirm_dialog()

    def pager_next(self) -> bool:
        """Go to next page."""
        return self.ui.pager_next()

    def pager_previous(self) -> bool:
        """Go to previous page."""
        return self.ui.pager_previous()

    def get_pager_info(self) -> dict[str, int]:
        """Get pager information."""
        return self.ui.get_pager_info()

    def search(self, query: str, clear_previous: bool = True) -> None:
        """Search in the list view."""
        self.ui.search(query, clear_previous)

    def filter_by(self, filter_name: str) -> None:
        """Apply a filter."""
        self.ui.filter_by(filter_name)

    def group_by(self, field_name: str) -> None:
        """Group by a field."""
        self.ui.group_by(field_name)

    def is_empty(self) -> bool:
        """Check if the list is empty."""
        return self.page.locator(".o_nocontent_help, .oe_nocontent").count() > 0

    def sort_by(self, column: str) -> None:
        """Sort by a column."""
        header = self.page.locator(f"th[data-field='{column}'], th[name='{column}']")
        header.click()
        self.ui.wait.for_ajax()


class KanbanView(BaseView):
    """Kanban view helper class."""

    def create(self, **fields: Any) -> None:
        """Click create and fill the form."""
        self.ui.click_create()
        form = FormView(self.ui, self.model)
        form.fill(**fields)
        form.save()

    def get_card_count(self) -> int:
        """Get the total number of cards."""
        return self.ui.get_kanban_card_count()

    def get_cards(self) -> Locator:
        """Get all kanban cards."""
        return self.ui.get_kanban_cards()

    def open_card(self, card_index: int = 0) -> FormView:
        """Open a kanban card."""
        self.ui.open_kanban_card(card_index)
        return FormView(self.ui, self.model)

    def get_column_count(self) -> int:
        """Get the number of columns."""
        return self.page.locator(self.selectors.get("kanban_column")).count()

    def get_column_cards(self, column_name: str) -> Locator:
        """Get cards in a specific column."""
        return self.page.locator(
            f".o_kanban_group:has(.o_column_title:has-text('{column_name}')) .o_kanban_record"
        )

    def move_card_to_column(self, card_title: str, column_name: str) -> None:
        """Drag and drop a card to another column."""
        card = self.page.locator(f".o_kanban_record:has-text('{card_title}')").first
        column = self.page.locator(f".o_kanban_group:has(.o_column_title:has-text('{column_name}'))")

        card.drag_to(column)
        self.ui.wait.for_ajax()

    def quick_create(self, column_name: Optional[str] = None, **fields: Any) -> None:
        """Create a card using quick create in a column."""
        if column_name:
            column = self.page.locator(
                f".o_kanban_group:has(.o_column_title:has-text('{column_name}'))"
            )
            add_btn = column.locator(".o_kanban_quick_add")
            add_btn.click()
        else:
            self.page.locator(".o_kanban_quick_add").first.click()

        self.ui.wait.for_ajax()

        for field_name, value in fields.items():
            input_field = self.page.locator(f".o_kanban_quick_create [name='{field_name}']")
            if input_field.count() > 0:
                input_field.fill(str(value))

        self.page.locator(".o_kanban_quick_create button[type='submit'], .o_kanban_quick_create .btn-primary").click()
        self.ui.wait.for_all()

    def search(self, query: str, clear_previous: bool = True) -> None:
        """Search in the kanban view."""
        self.ui.search(query, clear_previous)

    def filter_by(self, filter_name: str) -> None:
        """Apply a filter."""
        self.ui.filter_by(filter_name)

    def group_by(self, field_name: str) -> None:
        """Group by a field."""
        self.ui.group_by(field_name)
