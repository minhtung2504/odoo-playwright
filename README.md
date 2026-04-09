# Odoo Playwright

Tools to interact with Odoo UI using Playwright. Supports Odoo versions 16, 17, 18, and 19.

## Features

- 🚀 **Modern Playwright API** - Both sync and async support
- 🔧 **Version-aware selectors** - Automatic selector handling for Odoo 16-19
- 📦 **Page Object Model** - Clean abstraction for Odoo views
- ✅ **Pytest integration** - Ready-to-use fixtures
- 🔄 **Wait utilities** - Smart waiting for Odoo's AJAX/async operations
- 📸 **Screenshot support** - Easy debugging with screenshots

## Installation

```bash
pip install odoo-playwright
playwright install
```

## Quick Start

### Basic Usage

```python
from playwright.sync_api import sync_playwright
from odoo_playwright import OdooUI

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    ui = OdooUI(page, base_url="http://localhost:8069", version=17)
    ui.login("admin", "admin", "mydb")
    
    # Navigate to an app
    ui.go_to_app("Sales")
    
    # Create a record
    ui.click_create()
    ui.fill_field("name", "My New Partner")
    ui.click_save()
    
    browser.close()
```

### Using with Pytest

```python
import pytest

def test_create_partner(odoo_ui):
    """Test creating a partner."""
    odoo_ui.go_to_app("Contacts")
    
    odoo_ui.click_create()
    odoo_ui.fill_field("name", "Test Partner")
    odoo_ui.click_save()
    
    notification = odoo_ui.wait_for_notification()
    assert notification is None or notification["type"] == "success"
```

### Async Usage

```python
from playwright.async_api import async_playwright
from odoo_playwright.ui_async import AsyncOdooUI

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        ui = AsyncOdooUI(page, base_url="http://localhost:8069", version=17)
        await ui.login("admin", "admin", "mydb")
        
        await ui.go_to_app("Sales")
        
        # Create a record
        await ui.click_create()
        await ui.fill_field("name", "My New Partner")
        await ui.click_save()
        
        await browser.close()
```

### Page Object Model

```python
from odoo_playwright import OdooUI
from odoo_playwright.views import FormView, ListView

# Use page objects for cleaner code
ui.go_to_app("Contacts")
list_view = ListView(ui, "res.partner")

# Search and click a row
list_view.search("My Partner")
form = list_view.click_row_by_value("name", "My Partner")

# Edit the record
form.edit()
form.fill_field("email", "test@example.com")
form.save()
```

### Form View Operations

```python
# Create with data
form = FormView(ui, "res.partner")
form.create(
    name="John Doe",
    email="john@example.com",
    phone="+1234567890",
)

# Work with tabs
form.go_to_tab("Sales & Purchase")

# Work with one2many fields
form.add_one2many_item("child_ids")
# Fill the inline form...

# Upload files
form.upload_file("image_1920", "/path/to/image.png")
```

### List View Operations

```python
list_view = ListView(ui, "res.partner")

# Get all values
rows = list_view.get_values()
for row in rows:
    print(row)

# Select and delete
list_view.select_rows_by_value("name", "Test Partner")
list_view.delete_selected()

# Pagination
list_view.pager_next()
info = list_view.get_pager_info()
print(f"Showing {info['from']}-{info['to']} of {info['total']}")
```

### Kanban View Operations

```python
kanban = KanbanView(ui, "project.task")

# Get card count
count = kanban.get_card_count()

# Open a card
form = kanban.open_card(0)

# Quick create
kanban.quick_create(column_name="To Do", name="New Task")

# Drag and drop
kanban.move_card_to_column("My Task", "In Progress")
```

## Configuration

### Environment Variables

```bash
ODOO_URL=http://localhost:8069
ODOO_USER=admin
ODOO_PASSWORD=admin
ODOO_DB=test
ODOO_VERSION=17
HEADLESS=true
SLOW_MO=0
```

### Pytest Configuration

Create a `pytest.ini` or add to `pyproject.toml`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

## API Reference

### OdooUI

Main class for interacting with Odoo UI.

| Method | Description |
|--------|-------------|
| `login(username, password, database)` | Login to Odoo |
| `logout()` | Logout from Odoo |
| `go_to_app(app_name)` | Navigate to an app |
| `go_to_menu(*menu_path)` | Navigate through menu hierarchy |
| `switch_view(view_type)` | Switch to list/form/kanban view |
| `click_create()` | Click Create button |
| `click_save()` | Click Save button |
| `click_edit()` | Click Edit button |
| `click_discard()` | Click Discard button |
| `click_delete(confirm)` | Click Delete button |
| `fill_field(name, value)` | Fill a field |
| `fill_many2one(name, value)` | Fill a many2one field |
| `get_field_value(name)` | Get field value |
| `search(query, clear_previous)` | Search in current view |
| `filter_by(filter_name)` | Apply a filter |
| `group_by(field_name)` | Group by a field |
| `get_list_rows()` | Get list view rows |
| `get_list_values(columns)` | Get list view values |
| `click_list_row(index)` | Click a list row |
| `get_kanban_cards()` | Get kanban cards |
| `open_kanban_card(index)` | Open a kanban card |
| `is_modal_open()` | Check if modal is open |
| `close_modal(save)` | Close modal dialog |
| `wait_for_notification(timeout)` | Wait for notification |

### View Classes

#### FormView

| Method | Description |
|--------|-------------|
| `create(**fields)` | Create new record |
| `edit()` | Enter edit mode |
| `save()` | Save changes |
| `discard()` | Discard changes |
| `delete(confirm)` | Delete record |
| `go_to_tab(tab_name)` | Navigate to tab |
| `add_one2many_item(field)` | Add item to one2many |
| `get_one2many_values(field, columns)` | Get one2many values |
| `upload_file(field, path)` | Upload file |

#### ListView

| Method | Description |
|--------|-------------|
| `create(**fields)` | Create new record |
| `get_row_count()` | Get row count |
| `get_values(columns)` | Get all values |
| `click_row(index)` | Click row by index |
| `click_row_by_value(column, value)` | Click row by value |
| `select_row(index)` | Select row |
| `select_all()` | Select all rows |
| `delete_selected()` | Delete selected rows |
| `pager_next()` | Go to next page |
| `pager_previous()` | Go to previous page |
| `sort_by(column)` | Sort by column |

#### KanbanView

| Method | Description |
|--------|-------------|
| `create(**fields)` | Create new record |
| `get_card_count()` | Get card count |
| `open_card(index)` | Open card by index |
| `move_card_to_column(card, column)` | Drag card to column |
| `quick_create(column_name, **fields)` | Quick create card |

## Wait Utilities

Odoo uses AJAX and async operations. Use wait utilities to handle them:

```python
# Wait helpers
ui.wait.for_loading()      # Wait for loading overlay
ui.wait.for_ajax()         # Wait for AJAX requests
ui.wait.for_odoo_ready()   # Wait for Odoo JS framework
ui.wait.for_all()          # Wait for everything
ui.wait.for_selector(css)  # Wait for element
ui.wait.for_text(text)     # Wait for text to appear

# Context manager for AJAX
with ui.expect_ajax():
    ui.click_button("Save")
```

## Selectors by Version

The library includes version-specific selectors for Odoo 16-19:

```python
from odoo_playwright.selectors import get_selectors

selectors = get_selectors(17)
menu_selector = selectors.get("menu_item")
```

## Examples

### Test Sales Order Creation

```python
def test_create_sale_order(odoo_ui):
    odoo_ui.go_to_app("Sales")
    odoo_ui.go_to_menu("Orders", "Quotations")
    
    odoo_ui.click_create()
    
    odoo_ui.fill_many2one("partner_id", "My Customer")
    odoo_ui.fill_field("validity_date", "2024-12-31")
    
    # Add order line
    odoo_ui.page.locator(".o_field_one2many [name='add_item']").click()
    odoo_ui.fill_many2one("product_id", "Product A")
    odoo_ui.fill_field("product_uom_qty", 2)
    
    odoo_ui.click_save()
    
    notification = odoo_ui.wait_for_notification()
    assert notification["type"] == "success"
```

### Test User Creation

```python
def test_create_user(odoo_ui):
    odoo_ui.go_to_app("Settings")
    odoo_ui.go_to_menu("Users", "Users")
    
    odoo_ui.click_create()
    
    odoo_ui.fill_field("name", "Test User")
    odoo_ui.fill_field("login", "testuser")
    odoo_ui.fill_field("email", "testuser@example.com")
    
    odoo_ui.go_to_tab("Access Rights")
    odoo_ui.fill_field("sel_groups_1_8_9", "Administration: Settings")
    
    odoo_ui.click_save()
```

## License

MIT License

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## Credits

Inspired by [odooselenium](https://github.com/meta-it/odooselenium).
