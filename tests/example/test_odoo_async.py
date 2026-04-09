"""Async example tests for Odoo Playwright."""

import pytest
from odoo_playwright.ui_async import AsyncOdooUI


class TestAsyncOdooLogin:
    """Async test Odoo login functionality."""

    async def test_async_login_success(self, async_odoo_ui: AsyncOdooUI):
        """Test async successful login."""
        assert async_odoo_ui.page.url.endswith("/web")
        count = await async_odoo_ui.page.locator(".o_user_menu, .oe_topbar_name").count()
        assert count > 0

    async def test_async_logout(self, async_odoo_ui: AsyncOdooUI):
        """Test async logout."""
        await async_odoo_ui.logout()
        await async_odoo_ui.page.wait_for_url("**/web/login**")
        assert "login" in async_odoo_ui.page.url


class TestAsyncOdooNavigation:
    """Async test Odoo navigation."""

    async def test_async_go_to_app(self, async_odoo_ui: AsyncOdooUI):
        """Test async navigating to an app."""
        await async_odoo_ui.go_to_app("Settings")
        count = await async_odoo_ui.page.locator(".o_menu_entry").count()
        assert count > 0

    async def test_async_go_to_menu_path(self, async_odoo_ui: AsyncOdooUI):
        """Test async navigating through menu path."""
        await async_odoo_ui.go_to_app("Settings")
        await async_odoo_ui.go_to_menu("Users", "Users")
        count = await async_odoo_ui.page.locator(".o_data_row, .o_kanban_record").count()
        assert count >= 0


class TestAsyncOdooListView:
    """Async test Odoo list view operations."""

    async def test_async_list_view_search(self, async_odoo_ui: AsyncOdooUI):
        """Test async searching in list view."""
        await async_odoo_ui.go_to_app("Settings")
        await async_odoo_ui.go_to_menu("Users", "Users")
        await async_odoo_ui.switch_view("list")
        await async_odoo_ui.search("admin")
        count = await async_odoo_ui.get_list_row_count()
        assert count >= 1


class TestAsyncOdooFormView:
    """Async test Odoo form view operations."""

    async def test_async_create_partner(self, async_odoo_ui: AsyncOdooUI):
        """Test async creating a partner."""
        await async_odoo_ui.go_to_app("Contacts")
        await async_odoo_ui.click_create()

        await async_odoo_ui.fill_field("name", "Test Partner Async")
        await async_odoo_ui.click_save()

        notification = await async_odoo_ui.wait_for_notification()
        assert notification is None or notification["type"] != "error"

        await async_odoo_ui.click_delete(confirm=True)


class TestAsyncOdooViewObject:
    """Async test view object model."""

    async def test_async_form_view_create(self, async_odoo_ui: AsyncOdooUI):
        """Test async form view object create method."""
        from odoo_playwright.views_async import AsyncFormView

        await async_odoo_ui.go_to_app("Contacts")

        view = AsyncFormView(async_odoo_ui, "res.partner")
        await view.create(name="Test Partner Async via View Object")

        notification = await async_odoo_ui.wait_for_notification()
        assert notification is None or notification["type"] != "error"

        await async_odoo_ui.click_delete(confirm=True)
