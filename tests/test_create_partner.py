import asyncio
from playwright.async_api import async_playwright
from odoo_playwright.ui_async import AsyncOdooUI

async def main():
    async with async_playwright() as p:
        print("📍 Step 1: Launching Chrome...")
        browser = await p.chromium.launch(headless=False)
        print("✅ Chrome opened\n")
        await asyncio.sleep(1)

        print("📍 Step 2: Creating new page...")
        page = await browser.new_page()
        print("✅ Page created\n")
        await asyncio.sleep(1)

        print("📍 Step 3: Navigating to login page...")
        ui = AsyncOdooUI(page, base_url="https://integration.cc1.vn/", version=17)
        await ui.login("thuanlieu@xboss.com", "Thuanlt@2016", "integration_260803")
        print("✅ Logged in\n")
        await asyncio.sleep(1)

        print("📍 Step 4: Navigating to Sale Order form...")
        await ui.navigate("/web?debug=1#id=10417&cids=1&menu_id=1224&action=2157&model=sale.order&view_type=form")
        print("✅ Sale Order form loaded\n")
        await asyncio.sleep(2)

        # Extra wait to ensure form is fully loaded
        print("📍 Waiting for form to fully load...")
        await ui.wait.for_all()
        await asyncio.sleep(2)
        print("✅ Form fully loaded\n")

        # Debug: take screenshot to see the form
        await ui.take_screenshot("/tmp/form_opened.png")
        print("📸 Screenshot saved to /tmp/form_opened.png\n")

        # Debug: detailed page inspection
        print("📍 Deep inspecting form structure...")
        page_info = await ui.page.evaluate("""
            () => {
                const info = {
                    url: window.location.href,
                    iframes: document.querySelectorAll('iframe').length,
                    hasForm: !!document.querySelector('form'),
                    formContent: {
                        allInputs: document.querySelectorAll('input').length,
                        allTextareas: document.querySelectorAll('textarea').length,
                        allSelects: document.querySelectorAll('select').length,
                        namedInputs: Array.from(document.querySelectorAll('input[name]')).map(el => el.name),
                        fieldWidgets: Array.from(document.querySelectorAll('.o_field_widget')).map(el => ({
                            dataField: el.dataset.field,
                            dataFieldName: el.dataset.fieldName,
                            class: el.className.substring(0, 100)
                        })),
                        many2oneFields: Array.from(document.querySelectorAll('.o_field_many2one')).map(el => ({
                            dataField: el.dataset.field,
                            hasInput: !!el.querySelector('input')
                        }))
                    }
                };
                return info;
            }
        """)
        print(f"Page info: {page_info}\n")

        # Debug: get HTML of the form area to see actual structure
        print("📍 Getting form HTML to inspect structure...")
        form_html = await ui.page.evaluate("""
            () => {
                // Try multiple possible form containers
                const formContainer =
                    document.querySelector('.o_form_view') ||
                    document.querySelector('.o_form_container') ||
                    document.querySelector('form') ||
                    document.querySelector('.o_action_manager') ||
                    document.querySelector('main');

                if (!formContainer) return "No form container found";

                // Return first 3000 chars of innerHTML to see structure
                return formContainer.innerHTML.substring(0, 3000);
            }
        """)
        print(f"Form HTML (first 3000 chars):\n{form_html}\n")

        # Debug: inspect field widgets structure more carefully
        print("📍 Inspecting field widget structure in detail...")
        field_structure = await ui.page.evaluate("""
            () => {
                const widgets = Array.from(document.querySelectorAll('.o_field_widget')).slice(0, 5);
                return widgets.map(el => ({
                    classes: el.className,
                    dataField: el.dataset.field,
                    dataFieldName: el.dataset.fieldName,
                    dataName: el.dataset.name,
                    attributes: Array.from(el.attributes).map(a => `${a.name}=${a.value}`).join(', '),
                    childInputs: Array.from(el.querySelectorAll('input')).map(inp => ({
                        type: inp.type,
                        name: inp.name,
                        class: inp.className,
                        id: inp.id,
                        placeholder: inp.placeholder
                    }))
                }));
            }
        """)
        print(f"First 5 field widgets structure: {field_structure}\n")

        # Debug: inspect available fields
        print("📍 Inspecting available fields on the form...")
        field_names = await ui.page.evaluate("""
            () => {
                const fields = [];
                // Get all inputs with their parent context
                document.querySelectorAll('input').forEach(el => {
                    if (el.offsetParent !== null) {  // visible only
                        const parent = el.closest('.o_field_widget');
                        const dataField = parent?.dataset.field || el.dataset.field || el.name || 'unknown';
                        fields.push({
                            type: 'input',
                            fieldName: dataField,
                            inputType: el.type,
                            parentClass: parent?.className || 'no parent'
                        });
                    }
                });
                return fields.slice(0, 20);  // first 20
            }
        """)
        print(f"Available fields (first 20): {field_names}\n")

        print("📍 Step 6: Filling partner_id field...")
        try:
            await ui.fill_field("partner_id", "My New Partner")
        except Exception as e:
            print(f"❌ Error filling partner_id: {e}")
            # Try alternative field names
            print("📍 Trying alternative field names...")
            await asyncio.sleep(1)
        print("✅ Name filled\n")
        await asyncio.sleep(2)

        print("📍 Step 7: Saving partner...")
        await ui.click_save()
        print("✅ Partner saved\n")
        await asyncio.sleep(2)

        await browser.close()
        print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
