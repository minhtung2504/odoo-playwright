"""Wait utilities for Odoo Playwright."""


from playwright.async_api import Locator, Page
from playwright.sync_api import Locator as SyncLocator
from playwright.sync_api import Page as SyncPage


async def wait_for_odbus_async(page: Page, timeout: int = 30000) -> None:
    await page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.bus && !odoo.bus.is_busy",
        timeout=timeout,
    )


def wait_for_odbus(page: SyncPage, timeout: int = 30000) -> None:
    page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.bus && !odoo.bus.is_busy",
        timeout=timeout,
    )


async def wait_for_no_ajax_async(page: Page, timeout: int = 30000) -> None:
    await page.wait_for_function(
        "() => {"
        "  if (typeof jQuery !== 'undefined') {"
        "    return jQuery.active === 0;"
        "  }"
        "  return typeof odoo === 'undefined' || !odoo.loading || odoo.loading === 0;"
        "}",
        timeout=timeout,
    )


def wait_for_no_ajax(page: SyncPage, timeout: int = 30000) -> None:
    page.wait_for_function(
        "() => {"
        "  if (typeof jQuery !== 'undefined') {"
        "    return jQuery.active === 0;"
        "  }"
        "  return typeof odoo === 'undefined' || !odoo.loading || odoo.loading === 0;"
        "}",
        timeout=timeout,
    )


async def wait_for_not_loading_async(page: Page, timeout: int = 30000) -> None:
    await page.wait_for_function(
        "() => !document.body.classList.contains('oe_wait') && "
        "!document.querySelector('.o_loading:not(.o_hidden)')",
        timeout=timeout,
    )


def wait_for_not_loading(page: SyncPage, timeout: int = 30000) -> None:
    page.wait_for_function(
        "() => !document.body.classList.contains('oe_wait') && "
        "!document.querySelector('.o_loading:not(.o_hidden)')",
        timeout=timeout,
    )


async def wait_for_animation_async(page: Page, timeout: int = 5000) -> None:
    await page.wait_for_function(
        "() => !document.querySelector('.o_animate, .o_animating')",
        timeout=timeout,
    )


def wait_for_animation(page: SyncPage, timeout: int = 5000) -> None:
    page.wait_for_function(
        "() => !document.querySelector('.o_animate, .o_animating')",
        timeout=timeout,
    )


async def wait_for_odooready_async(page: Page, timeout: int = 30000) -> None:
    await page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.isReady",
        timeout=timeout,
    )


def wait_for_odooready(page: SyncPage, timeout: int = 30000) -> None:
    page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.isReady",
        timeout=timeout,
    )


async def wait_for_router_async(page: Page, timeout: int = 10000) -> None:
    await page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.router && !odoo.router._pending",
        timeout=timeout,
    )


def wait_for_router(page: SyncPage, timeout: int = 10000) -> None:
    page.wait_for_function(
        "() => typeof odoo !== 'undefined' && odoo.router && !odoo.router._pending",
        timeout=timeout,
    )


class WaitHelper:
    def __init__(self, page: SyncPage):
        self.page = page

    def for_loading(self, timeout: int = 30000) -> None:
        wait_for_not_loading(self.page, timeout)

    def for_ajax(self, timeout: int = 30000) -> None:
        wait_for_no_ajax(self.page, timeout)

    def for_odoo_ready(self, timeout: int = 30000) -> None:
        wait_for_odooready(self.page, timeout)

    def for_router(self, timeout: int = 10000) -> None:
        wait_for_router(self.page, timeout)

    def for_animation(self, timeout: int = 5000) -> None:
        wait_for_animation(self.page, timeout)

    def for_all(self, timeout: int = 30000) -> None:
        self.for_odoo_ready(timeout)
        self.for_loading(timeout)
        self.for_ajax(timeout)
        self.for_animation(timeout)

    def for_selector(self, selector: str, timeout: int = 10000) -> SyncLocator:
        return self.page.locator(selector).wait_for(timeout=timeout)

    def for_selector_hidden(self, selector: str, timeout: int = 10000) -> None:
        self.page.locator(selector).wait_for(state="hidden", timeout=timeout)

    def for_text(self, text: str, timeout: int = 10000) -> SyncLocator:
        return self.page.get_by_text(text).first.wait_for(timeout=timeout)

    def for_url(self, pattern: str, timeout: int = 30000) -> None:
        self.page.wait_for_url(f"**/{pattern}*", timeout=timeout)


class AsyncWaitHelper:
    def __init__(self, page: Page):
        self.page = page

    async def for_loading(self, timeout: int = 30000) -> None:
        await wait_for_not_loading_async(self.page, timeout)

    async def for_ajax(self, timeout: int = 30000) -> None:
        await wait_for_no_ajax_async(self.page, timeout)

    async def for_odoo_ready(self, timeout: int = 30000) -> None:
        await wait_for_odooready_async(self.page, timeout)

    async def for_router(self, timeout: int = 10000) -> None:
        await wait_for_router_async(self.page, timeout)

    async def for_animation(self, timeout: int = 5000) -> None:
        await wait_for_animation_async(self.page, timeout)

    async def for_all(self, timeout: int = 30000) -> None:
        await self.for_odoo_ready(timeout)
        await self.for_loading(timeout)
        await self.for_ajax(timeout)
        await self.for_animation(timeout)

    async def for_selector(self, selector: str, timeout: int = 10000) -> Locator:
        return await self.page.locator(selector).wait_for(timeout=timeout)

    async def for_selector_hidden(self, selector: str, timeout: int = 10000) -> None:
        await self.page.locator(selector).wait_for(state="hidden", timeout=timeout)

    async def for_text(self, text: str, timeout: int = 10000) -> Locator:
        return await self.page.get_by_text(text).first.wait_for(timeout=timeout)

    async def for_url(self, pattern: str, timeout: int = 30000) -> None:
        await self.page.wait_for_url(f"**/{pattern}*", timeout=timeout)
