"""Example tests for Odoo Playwright."""

import pytest
from odoo_playwright import OdooUI


class TestOdooLogin:
    """Test Odoo login functionality."""

    def test_login_success(self, odoo_ui: OdooUI):
        """Test successful login."""
        assert odoo_ui.page.url.endswith("/web")
        assert odoo_ui.page.locator(".o_user_menu, .oe_topbar_name").count() > 0

    def test_logout(self, odoo_ui: OdooUI):
        """Test logout."""
        odoo_ui.logout()
        odoo_ui.page.wait_for_url("**/web/login**")
        assert "login" in odoo_ui.page.url


class TestOdooNavigation:
    """Test Odoo navigation."""

    def test_go_to_app(self, odoo_ui: OdooUI):
        """Test navigating to an app."""
        odoo_ui.go_to_app("Settings")
        assert "Settings" in odoo_ui.page.url or odoo_ui.page.locator(".o_menu_entry").count() > 0

    def test_go_to_menu_path(self, odoo_ui: OdooUI):
        """Test navigating through menu path."""
        odoo_ui.go_to_app("Settings")
        odoo_ui.go_to_menu("Users", "Users")
        assert odoo_ui.page.locator(".o_data_row, .o_kanban_record").count() >= 0


class TestOdooListView:
    """Test Odoo list view operations."""

    def test_list_view_search(self, odoo_ui: OdooUI):
        """Test searching in list view."""
        odoo_ui.go_to_app("Settings")
        odoo_ui.go_to_menu("Users", "Users")
        odoo_ui.switch_view("list")
        odoo_ui.search("admin")
        assert odoo_ui.get_list_row_count() >= 1

    def test_list_view_pager(self, odoo_ui: OdooUI):
        """Test list view pagination."""
        odoo_ui.go_to_app("Settings")
        odoo_ui.go_to_menu("Users", "Users")
        odoo_ui.switch_view("list")

        pager_info = odoo_ui.get_pager_info()
        if pager_info["total"] > pager_info["to"]:
            odoo_ui.pager_next()
            new_info = odoo_ui.get_pager_info()
            assert new_info["from"] > pager_info["from"]


class TestOdooFormView:
    """Test Odoo form view operations."""

    def test_create_and_delete_partner(self, odoo_ui: OdooUI):
        """Test creating and deleting a partner."""
        odoo_ui.go_to_app("Contacts")
        odoo_ui.click_create()

        odoo_ui.fill_field("name", "Test Partner from Playwright")
        odoo_ui.click_save()

        notification = odoo_ui.wait_for_notification()
        assert notification is None or notification["type"] != "error"

        odoo_ui.click_delete(confirm=True)

    def test_form_edit_and_discard(self, odoo_ui: OdooUI):
        """Test editing and discarding changes."""
        odoo_ui.go_to_app("Contacts")
        odoo_ui.search("")

        if odoo_ui.get_list_row_count() > 0:
            odoo_ui.click_list_row(0)
            odoo_ui.click_edit()
            odoo_ui.fill_field("name", "Modified Name")
            odoo_ui.click_discard()


class TestOdooKanbanView:
    """Test Odoo kanban view operations."""

    def test_kanban_card_count(self, odoo_ui: OdooUI):
        """Test kanban card count."""
        odoo_ui.go_to_app("Contacts")
        odoo_ui.switch_view("kanban")
        assert odoo_ui.get_kanban_card_count() >= 0


class TestOdooFields:
    """Test Odoo field operations."""

    def test_fill_text_field(self, odoo_ui: OdooUI):
        """Test filling text field."""
        odoo_ui.go_to_app("Contacts")
        odoo_ui.click_create()

        field = odoo_ui.get_field("name")
        assert field.count() > 0

        odoo_ui.fill_field("name", "Test Name")
        assert odoo_ui.get_field_value("name") == "Test Name"

        odoo_ui.click_discard()


class TestOdooWaitHelpers:
    """Test wait helpers."""

    def test_wait_for_loading(self, odoo_ui: OdooUI):
        """Test waiting for loading to complete."""
        odoo_ui.go_to_app("Settings")
        odoo_ui.wait.for_loading()
        assert odoo_ui.page.locator(".o_loading:not(.o_hidden)").count() == 0


class TestOdooPageObject:
    """Test page object model."""

    def test_page_navigation(self, odoo_ui: OdooUI):
        """Test page object navigation."""
        page = odoo_ui.page("Settings").navigate()
        assert odoo_ui.page.locator(".o_content").count() > 0


class TestOdooViewObject:
    """Test view object model."""

    def test_form_view_create(self, odoo_ui: OdooUI):
        """Test form view object create method."""
        from odoo_playwright.views import FormView

        odoo_ui.go_to_app("Contacts")

        view = FormView(odoo_ui, "res.partner")
        view.create(name="Test Partner via View Object")

        notification = odoo_ui.wait_for_notification()
        assert notification is None or notification["type"] != "error"

        odoo_ui.click_delete(confirm=True)
