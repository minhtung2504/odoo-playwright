"""Pytest fixtures for Odoo Playwright testing."""

import os
from pathlib import Path

import pytest
from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import Playwright as AsyncPlaywright
from playwright.async_api import async_playwright
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from odoo_playwright.testcase import OdooConfig
from odoo_playwright.ui import OdooUI
from odoo_playwright.ui_async import AsyncOdooUI

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines from ``path`` into os.environ.

    Variables already set in the shell ($env:, setx, export) win over the file.
    Blank lines and lines starting with '#' are ignored; an optional 'export '
    prefix and surrounding quotes around the value are stripped.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


load_env_file(ENV_FILE)


def pytest_addoption(parser):
    parser.addoption(
        "--invoice",
        action="append",
        default=[],
        help="Vendor invoice PDF file or folder (repeatable) for test_create_po_from_vendor_invoice.",
    )
    parser.addoption(
        "--stop-at-po",
        action="store_true",
        help="Invoice test: stop after confirming the PO (no receipt, no bill).",
    )
    parser.addoption(
        "--pay",
        action="store_true",
        help="Also register the payment of the posted vendor bill.",
    )


def get_config() -> OdooConfig:
    """Get Odoo configuration from environment."""
    return OdooConfig.from_env()


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Default browser launch arguments."""
    return {
        "headless": os.getenv("HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.getenv("SLOW_MO", "0")),
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Default browser context arguments."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
        "timezone_id": "UTC",
    }


@pytest.fixture(scope="session")
def playwright():
    """Create Playwright instance."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args):
    """Create browser instance."""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser, browser_context_args):
    """Create browser context."""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """Create a new page."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def odoo_config() -> OdooConfig:
    """Get Odoo configuration."""
    return get_config()


@pytest.fixture
def odoo_ui(page: Page, odoo_config: OdooConfig) -> OdooUI:
    """Create OdooUI instance and login."""
    ui = OdooUI(
        page=page,
        base_url=odoo_config.base_url,
        version=odoo_config.version,
    )
    ui.login(
        username=odoo_config.username,
        password=odoo_config.password,
        database=odoo_config.database,
    )
    yield ui


@pytest.fixture
def odoo_page(odoo_ui: OdooUI):
    """Get a page object for navigation."""
    return odoo_ui


@pytest.fixture(scope="function")
async def async_playwright_instance():
    """Create async Playwright instance."""
    async with async_playwright() as p:
        yield p


@pytest.fixture(scope="function")
async def async_browser(async_playwright_instance: AsyncPlaywright, browser_type_launch_args):
    """Create async browser instance."""
    browser = await async_playwright_instance.chromium.launch(**browser_type_launch_args)
    yield browser
    await browser.close()


@pytest.fixture(scope="function")
async def async_context(async_browser: AsyncBrowser, browser_context_args):
    """Create async browser context."""
    context = await async_browser.new_context(**browser_context_args)
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def async_page(async_context):
    """Create async page."""
    page = await async_context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def async_odoo_ui(async_page, odoo_config: OdooConfig) -> AsyncOdooUI:
    """Create AsyncOdooUI instance and login."""
    ui = AsyncOdooUI(
        page=async_page,
        base_url=odoo_config.base_url,
        version=odoo_config.version,
    )
    await ui.login(
        username=odoo_config.username,
        password=odoo_config.password,
        database=odoo_config.database,
    )
    yield ui


@pytest.fixture
def screenshot_on_failure(page: Page, request):
    """Take screenshot on test failure."""
    yield
    if request.node.rep_call.failed:
        screenshot_dir = "screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"{request.node.name}.png")
        page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved to: {screenshot_path}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to get test result for screenshot_on_failure."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
