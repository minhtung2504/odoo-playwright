"""Page object model for Odoo UI."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_playwright.ui import OdooUI


class OdooPage:
    """Represents an Odoo app/page."""

    def __init__(self, ui: "OdooUI", name: str):
        self.ui = ui
        self.page = ui.page
        self.name = name
        self._navigated = False

    def navigate(self) -> "OdooPage":
        """Navigate to this page/app."""
        self.ui.go_to_app(self.name)
        self._navigated = True
        return self

    def menu(self, *menu_path: str) -> "OdooPage":
        """Navigate to a submenu within this page."""
        if not self._navigated:
            self.navigate()
        self.ui.go_to_menu(*menu_path)
        return self

    def view(self, model: str, view_type: str = "form"):
        """Get a view object for a model."""
        from odoo_playwright.views import FormView, KanbanView, ListView

        view_classes = {
            "form": FormView,
            "list": ListView,
            "tree": ListView,
            "kanban": KanbanView,
        }

        view_class = view_classes.get(view_type, FormView)
        return view_class(self.ui, model)


class OdooSubMenu:
    """Represents a submenu within an Odoo page."""

    def __init__(self, parent: OdooPage, name: str):
        self.parent = parent
        self.ui = parent.ui
        self.page = parent.page
        self.name = name

    def click(self) -> "OdooSubMenu":
        """Click this menu item."""
        self.ui.go_to_menu(self.name)
        return self
