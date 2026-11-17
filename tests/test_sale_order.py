"""Create a Sale Order through the UI and verify it was saved.

Configure the data with environment variables (no credentials in code):
    SO_CUSTOMER  - existing customer name to pick (default: "Công ty ABC")
    SO_PRODUCT   - existing product name to pick (default: "Product Name")
    SO_QTY       - quantity on the order line (default: 1)
    SO_PRICE     - unit price on the order line (default: 100000)

Note: this writes a real sale.order to the database pointed at by the config.
"""

import os
import re

import pytest

from odoo_playwright.ui_async import AsyncOdooUI

pytestmark = pytest.mark.integration

CUSTOMER = os.getenv("SO_CUSTOMER", "Công ty ABC")
PRODUCT = os.getenv("SO_PRODUCT", "Product Name")
QTY = os.getenv("SO_QTY", "1")
PRICE = os.getenv("SO_PRICE", "100000")


async def create_sale_order(ui: AsyncOdooUI) -> None:
    """Open a new Sale Order form and fill one order line."""
    await ui.go_to_menu("Sales", "Orders")
    await ui.click_create()

    await ui.fill_field("partner_id", CUSTOMER)

    await ui.page.locator("[name='order_line'] .o_field_x2many_list_row_add a").click()
    await ui.wait.for_all()
    await ui.fill_field("product_id", PRODUCT)
    await ui.fill_field("product_uom_qty", QTY)
    await ui.fill_field("price_unit", PRICE)

    await ui.click_save()


class TestSaleOrder:
    """Create and verify a Sale Order."""

    async def test_create_sale_order(self, async_odoo_ui: AsyncOdooUI):
        """A Sale Order with a customer and one line is saved."""
        ui = async_odoo_ui
        await create_sale_order(ui)

        assert re.search(r"id=\d+", ui.page.url), "Sale Order was not saved (no record id in URL)"
        assert CUSTOMER in await ui.get_field_value("partner_id")
