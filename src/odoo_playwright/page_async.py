"""Async page object model for Odoo UI."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_playwright.ui_async import AsyncOdooUI


class AsyncOdooPage:
    """Async represents an Odoo app/page."""

    def __init__(self, ui: "AsyncOdooUI", name: str):
        self.ui = ui
        self.page = ui.page
        self.name = name
        self._navigated = False

    async def navigate(self) -> "AsyncOdooPage":
        """Navigate to this page/app."""
        await self.ui.go_to_app(self.name)
        self._navigated = True
        return self

    async def menu(self, *menu_path: str) -> "AsyncOdooPage":
        """Navigate to a submenu within this page."""
        if not self._navigated:
            await self.navigate()
        await self.ui.go_to_menu(*menu_path)
        return self

    def view(self, model: str, view_type: str = "form"):
        """Get a view object for a model."""
        from odoo_playwright.views_async import AsyncFormView, AsyncListView, AsyncKanbanView

        view_classes = {
            "form": AsyncFormView,
            "list": AsyncListView,
            "tree": AsyncListView,
            "kanban": AsyncKanbanView,
        }

        view_class = view_classes.get(view_type, AsyncFormView)
        return view_class(self.ui, model)
