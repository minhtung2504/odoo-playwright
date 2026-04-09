"""Test case base class for Odoo UI testing."""

import os
from typing import Any, Dict, Optional

from playwright.sync_api import Page, Browser, BrowserContext, Playwright, sync_playwright
import pytest


class OdooTestCase:
    """Base test case for Odoo UI tests with Playwright.

    Provides setup/teardown for Odoo login and common utilities.

    Usage with pytest:
        class TestMyFeature(OdooTestCase):
            def test_something(self, odoo_ui):
                odoo_ui.go_to_app("Sales")
                # ...
    """

    base_url: str = "http://localhost:8069"
    username: str = "admin"
    password: str = "admin"
    database: str = "test"
    version: int = 17
    headless: bool = True
    slow_mo: int = 0
    browser_type: str = "chromium"
    viewport: Dict[str, int] = {"width": 1280, "height": 720}
    locale: str = "en-US"
    timezone: str = "UTC"

    @pytest.fixture(autouse=True)
    def setup_playwright(self, playwright: Playwright, browser: Browser):
        """Setup playwright browser and page."""
        self.playwright = playwright
        self.browser = browser
        self.context = self._create_context()
        self.page = self.context.new_page()
        self.ui = self._create_ui()
        self._login()
        yield
        self._teardown()

    def _create_context(self) -> BrowserContext:
        """Create browser context with options."""
        return self.browser.new_context(
            viewport=self.viewport,
            locale=self.locale,
            timezone_id=self.timezone,
        )

    def _create_ui(self):
        """Create OdooUI instance."""
        from odoo_playwright.ui import OdooUI
        return OdooUI(
            page=self.page,
            base_url=self.base_url,
            version=self.version,
        )

    def _login(self):
        """Login to Odoo."""
        self.ui.login(self.username, self.password, self.database)

    def _teardown(self):
        """Cleanup after test."""
        self.context.close()

    def take_screenshot(self, name: str) -> None:
        """Take a screenshot with given name."""
        self.page.screenshot(path=f"screenshots/{name}.png")


class AsyncOdooTestCase:
    """Async base test case for Odoo UI tests with Playwright.

    Usage with pytest:
        class TestMyFeature(AsyncOdooTestCase):
            async def test_something(self, odoo_ui):
                await odoo_ui.go_to_app("Sales")
                # ...
    """

    base_url: str = "http://localhost:8069"
    username: str = "admin"
    password: str = "admin"
    database: str = "test"
    version: int = 17
    headless: bool = True
    slow_mo: int = 0
    browser_type: str = "chromium"
    viewport: Dict[str, int] = {"width": 1280, "height": 720}
    locale: str = "en-US"
    timezone: str = "UTC"

    @pytest.fixture(autouse=True)
    async def setup_playwright(self, playwright, browser):
        """Setup playwright browser and page."""
        self.playwright = playwright
        self.browser = browser
        self.context = await self._create_context()
        self.page = await self.context.new_page()
        self.ui = await self._create_ui()
        await self._login()
        yield
        await self._teardown()

    async def _create_context(self):
        """Create browser context with options."""
        return await self.browser.new_context(
            viewport=self.viewport,
            locale=self.locale,
            timezone_id=self.timezone,
        )

    async def _create_ui(self):
        """Create AsyncOdooUI instance."""
        from odoo_playwright.ui_async import AsyncOdooUI
        return AsyncOdooUI(
            page=self.page,
            base_url=self.base_url,
            version=self.version,
        )

    async def _login(self):
        """Login to Odoo."""
        await self.ui.login(self.username, self.password, self.database)

    async def _teardown(self):
        """Cleanup after test."""
        await self.context.close()

    async def take_screenshot(self, name: str) -> None:
        """Take a screenshot with given name."""
        await self.page.screenshot(path=f"screenshots/{name}.png")


class OdooConfig:
    """Configuration for Odoo test environment."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        version: Optional[int] = None,
    ):
        self.base_url = base_url or os.getenv("ODOO_URL", "http://localhost:8069")
        self.username = username or os.getenv("ODOO_USER", "admin")
        self.password = password or os.getenv("ODOO_PASSWORD", "admin")
        self.database = database or os.getenv("ODOO_DB", "test")
        self.version = version or int(os.getenv("ODOO_VERSION", "17"))

    @classmethod
    def from_env(cls) -> "OdooConfig":
        """Create config from environment variables."""
        return cls()
