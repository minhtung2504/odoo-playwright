import asyncio
from playwright.async_api import async_playwright
from odoo_playwright.testcase import OdooConfig
from odoo_playwright.ui_async import AsyncOdooUI

async def main():
    config = OdooConfig.from_env()
    async with async_playwright() as p:
        print("📍 Step 1: Launching Chrome...")
        browser = await p.chromium.launch(headless=False)
        print("✅ Chrome opened\n")
        await asyncio.sleep(1)

        print("📍 Step 2: Creating new page...")
        page = await browser.new_page()
        print("✅ Page created\n")
        await asyncio.sleep(1)

        print("📍 Step 3: Logging in...")
        ui = AsyncOdooUI(page, base_url=config.base_url, version=config.version)
        await ui.login(config.username, config.password, config.database)
        print("✅ Logged in\n")
        await asyncio.sleep(1)

        print("📍 Step 4: Expanding sidebar menu...")
        # Click the hamburger menu to expand sidebar if it's collapsed
        sidebar_toggle = ui.page.locator(".o_main_navbar .o_menu_toggle, [data-menu-xmlid='base.menu_toggle']")
        if await sidebar_toggle.count() > 0:
            await sidebar_toggle.click()
            await asyncio.sleep(1)
            print("✅ Sidebar expanded\n")

        print("📍 Step 5: Taking screenshot of menu...")
        await ui.take_screenshot("/tmp/menu_before.png")
        print("📸 Screenshot saved to /tmp/menu_before.png\n")

        print("📍 Step 6: Navigating to Sale Order list...")
        try:
            await ui.go_to_menu("Sales", "Orders", timeout=15000)
            print("✅ Sale Order list loaded\n")
        except Exception as e:
            print(f"❌ Error navigating to menu: {e}")
            print("📍 Trying Sales app via command palette...")
            await ui.go_to_app("Sales", timeout=15000)
            print("✅ Sales app opened\n")

        await asyncio.sleep(2)

        # Check if demo data modal appears and dismiss it
        print("📍 Checking for demo data modal...")
        demo_modal = ui.page.get_by_text("Oops, no!", exact=True)
        if await demo_modal.count() > 0:
            print("⚠️ Demo data modal found, dismissing...")
            await demo_modal.click()
            await asyncio.sleep(1)
            print("✅ Demo data modal dismissed\n")
        else:
            print("✅ No demo data modal\n")

        print("📍 Step 4b: Taking screenshot before creating...")
        await ui.take_screenshot("/tmp/so_list.png")
        print("📸 Screenshot saved to /tmp/so_list.png\n")

        print("📍 Step 5: Clicking Create button...")
        await ui.click_create()
        print("✅ Create button clicked\n")
        await asyncio.sleep(2)

        # Wait for form to load
        print("📍 Waiting for Sale Order form to load...")
        await ui.wait.for_all()
        await asyncio.sleep(2)
        print("✅ Form loaded\n")

        # Debug: take screenshot to see the form
        await ui.take_screenshot("/tmp/so_form_created.png")
        print("📸 Screenshot saved to /tmp/so_form_created.png\n")

        print("📍 Step 6: Filling Sale Order fields...")

        # Fill customer (partner_id)
        print("  - Filling Customer...")
        try:
            await ui.fill_field("partner_id", "Công ty ABC")
            print("  ✅ Customer filled")
        except Exception as e:
            print(f"  ❌ Error filling customer: {e}")
        await asyncio.sleep(1)

        # Add order lines
        print("  - Adding order lines...")
        try:
            # Click the add line button in the order lines section
            await ui.click_button("Add a line")
            print("  ✅ Order line added")
        except Exception as e:
            print(f"  ⚠️ Could not add order line: {e}")
        await asyncio.sleep(1)

        # Fill product
        print("  - Filling Product...")
        try:
            await ui.fill_field("product_id", "Product Name")
            print("  ✅ Product filled")
        except Exception as e:
            print(f"  ❌ Error filling product: {e}")
        await asyncio.sleep(1)

        # Fill quantity
        print("  - Filling Quantity...")
        try:
            await ui.fill_field("product_uom_qty", "1")
            print("  ✅ Quantity filled")
        except Exception as e:
            print(f"  ❌ Error filling quantity: {e}")
        await asyncio.sleep(1)

        # Fill unit price
        print("  - Filling Unit Price...")
        try:
            await ui.fill_field("price_unit", "100000")
            print("  ✅ Unit Price filled")
        except Exception as e:
            print(f"  ❌ Error filling unit price: {e}")
        await asyncio.sleep(1)

        print("\n📍 Step 7: Taking screenshot before saving...")
        await ui.take_screenshot("/tmp/so_form_filled.png")
        print("📸 Screenshot saved to /tmp/so_form_filled.png\n")

        print("📍 Step 8: Saving Sale Order...")
        await ui.click_save()
        print("✅ Sale Order saved\n")
        await asyncio.sleep(2)

        print("📍 Step 9: Taking final screenshot...")
        await ui.take_screenshot("/tmp/so_created.png")
        print("📸 Screenshot saved to /tmp/so_created.png\n")

        await browser.close()
        print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
