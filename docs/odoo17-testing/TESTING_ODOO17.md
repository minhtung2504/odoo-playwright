# Testing AsyncOdooUI for Odoo 17

This document explains how to verify and fix each function in `AsyncOdooUI` to ensure compatibility with Odoo 17.

## Quick Start

### 1. Set Environment Variables

```bash
# Point to your Odoo 17 instance
export ODOO_URL="https://integration.cc1.vn"
export ODOO_USER="your_username"
export ODOO_PASSWORD="your_password"
export ODOO_DB="your_database"
export ODOO_VERSION=17

# Optional: visual debugging
export HEADLESS=false      # See browser actions
export SLOW_MO=500         # 500ms pause between actions
```

### 2. Run Tests

```bash
# Quick validation (navigation only)
./scripts/run_odoo17_tests.sh quick

# Run specific test groups
./scripts/run_odoo17_tests.sh forms        # Form operations
./scripts/run_odoo17_tests.sh list         # List view operations
./scripts/run_odoo17_tests.sh modals       # Modal & notification tests

# Run all tests
./scripts/run_odoo17_tests.sh all

# Detailed output
pytest tests/test_verify_odoo17_functions.py -vvs
```

## Test Structure

The test suite is organized into 12 test classes, each focusing on a specific area:

### 1. **Navigation Tests** (`TestAsyncOdooUI_Navigation`)
Tests URL handling, fragments, and model detection:
- `navigate()` - Go to a path
- `get_url_fragments()` - Parse URL #hash
- `get_current_model()` - Extract model from form
- `get_current_view_type()` - Get list/form/kanban view type

**Expected**: Should work fine in Odoo 17 ✅

---

### 2. **App & Menu Navigation** (`TestAsyncOdooUI_AppNavigation`)
Tests command palette and menu traversal:
- `go_to_app()` - Open app via Cmd+K palette
- `go_to_menu()` - Navigate menu hierarchy

**Expected**: Should work fine in Odoo 17 ✅

---

### 3. **View Switching** (`TestAsyncOdooUI_ViewSwitching`)
Tests view type changes:
- `switch_view()` - Change to list/form/kanban

**Known Issues**: Selectors work but may need refinement

---

### 4. **Form Actions** (`TestAsyncOdooUI_FormActions`) ⚠️
Tests form buttons - **NEEDS FIXES**:
- `click_create()` - Create new record
- `click_save()` - Save record
- `click_edit()` - Enter edit mode
- `click_discard()` - Cancel changes
- `click_delete()` - **❌ BROKEN** - Delete moved to action menu in Odoo 17

**Issues Found**:
| Function | Issue | Fix |
|----------|-------|-----|
| `click_delete()` | Selector targets wrong button | Use `.o_cp_action_menus button` + find "Delete" text |
| `click_edit()` | May not exist if already editing | Add error handling |

---

### 5. **Field Operations** (`TestAsyncOdooUI_FieldOperations`) ⚠️
Tests reading/writing field values - **NEEDS FIXES**:
- `get_field()` - Locate field widget
- `fill_field()` - Set field value
- `get_field_value()` - Read field value
- `fill_many2one()` - Fill relationship field
- `clear_field()` - Clear a field

**Issues Found**:
| Function | Issue | Fix |
|----------|-------|-----|
| `fill_field()` - many2one detection | Parent structure check is incomplete | Check ancestor chain, not just parent |
| `get_field_value()` - select handling | `option:checked` may fail on custom selects | Add fallback to `data-value` attribute |
| `fill_many2one()` | Relies on deprecated `.ui-autocomplete` | Prioritize `.o_dropdown_menu` |

---

### 6. **Search & Filter** (`TestAsyncOdooUI_SearchAndFilter`)
Tests list view searching:
- `search()` - Search for values
- `clear_search()` - Clear filters
- `filter_by()` - Apply filters
- `group_by()` - Group by field

**Known Issues**: Search input may be hidden until search button clicked

---

### 7. **List View Operations** (`TestAsyncOdooUI_ListViewOperations`)
Tests table/list interactions:
- `get_list_rows()` - Get row locators
- `get_list_row_count()` - Count rows
- `click_list_row()` - Open record
- `get_list_values()` - Extract table data
- `pager_next/previous()` - Pagination

**Expected**: Should work fine in Odoo 17 ✅

---

### 8. **Kanban View** (`TestAsyncOdooUI_KanbanOperations`)
Tests kanban board operations:
- `get_kanban_cards()` - Get card locators
- `get_kanban_card_count()` - Count cards
- `open_kanban_card()` - Open card

**Expected**: Should work fine in Odoo 17 ✅

---

### 9. **Modals** (`TestAsyncOdooUI_Modals`)
Tests dialog/modal windows - **NEEDS FIXES**:
- `is_modal_open()` - Check if modal visible
- `close_modal()` - Close with save/cancel

**Issues Found**:
| Function | Issue | Fix |
|----------|-------|-----|
| `close_modal()` | Button selectors too permissive | Use more specific selectors for save/cancel |

---

### 10. **Notifications** (`TestAsyncOdooUI_Notifications`)
Tests toast/notification handling:
- `get_notification()` - Get current notification
- `wait_for_notification()` - Wait for notification
- `dismiss_notification()` - Close notification

**Expected**: Should work fine in Odoo 17 ✅

---

### 11. **Tabs & Buttons** (`TestAsyncOdooUI_TabOperations` + `TestAsyncOdooUI_ClickActions`)
Tests form tabs and action buttons:
- `go_to_tab()` - Switch form tabs
- `click_button()` - Click button by name
- `click_action()` - Click action from menu

**Known Issues**: 
- Tab selectors need Bootstrap 5 update
- Action button clicking depends on specific HTML structure

---

### 12. **Utilities** (`TestAsyncOdooUI_Utilities` + `TestAsyncOdooUI_ScreenshotAndDebug`)
Tests helper functions:
- `execute_js()` - Run JavaScript
- `get_odoo_version()` - Get version info
- `wait_for_url_contains()` - Wait for URL change
- `take_screenshot()` - Save screenshot
- `install_module()` - Install addon

**Expected**: Should work fine in Odoo 17 ✅

---

## Debugging Test Failures

### 1. **Check Visual Output**
```bash
# Run with browser visible
HEADLESS=false SLOW_MO=1000 pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs
```

### 2. **Debug Selector Issues**
```bash
# In test, use:
await async_odoo_ui.page.pause()  # Stops execution, open DevTools

# Or inspect the page:
elements = await async_odoo_ui.page.locator(".some-selector").count()
print(f"Found {elements} elements")
```

### 3. **Check Selector Availability**
Run in browser console:
```javascript
// Check if selector exists
document.querySelectorAll(".o_cp_action_menus button").length
document.querySelectorAll(".o_form_button_delete").length
document.querySelectorAll(".dropdown-item:contains('Delete')").length
```

---

## Known Odoo 17 Changes

### Bootstrap 5 Migration
- **Old**: `.navbar`, `.nav-pills` → **New**: `.navbar-expand`, `.nav`
- **Impact**: Tab and menu selectors changed

### jQuery UI → Modern JavaScript
- **Old**: `.ui-autocomplete`, `.ui-dialog` → **New**: `.o_dropdown_menu`, `.modal-dialog`
- **Impact**: Many2one and modal handling needs update

### Action Menu Restructure
- **Old**: Delete button as standalone → **New**: Delete in action menu dropdown
- **Impact**: `click_delete()` completely broken

### Field Widget Consistency
- Still uses `.o_field_widget` ✅
- But ancestor structure may differ in some cases

---

## Applying Fixes

### Fix Priority

1. **CRITICAL** (blocking tests):
   - [ ] `click_delete()` - Completely broken

2. **HIGH** (common operations):
   - [ ] `fill_many2one()` - Dropdown selector improvements
   - [ ] `close_modal()` - More robust button targeting
   - [ ] `get_field_value()` - Select element handling

3. **MEDIUM** (quality improvements):
   - [ ] `fill_field()` - Better many2one detection
   - [ ] `go_to_tab()` - Bootstrap 5 selectors
   - [ ] `search()` - Visibility check before filling

4. **LOW** (edge cases):
   - [ ] `click_edit()` - Error handling
   - [ ] `click_action()` - More specific action finding

### How to Apply

1. **Review** the detailed issues in `ODOO17_FIXES_NEEDED.md`
2. **Edit** `src/odoo_playwright/ui_async.py` with fixes
3. **Test** with: `./scripts/run_odoo17_tests.sh all`
4. **Verify** all tests pass

---

## Example: Fixing `click_delete()`

### Before (Broken):
```python
async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
    delete_btn = self.page.locator(self.selectors.get("button_delete"))
    await delete_btn.click()
    # ❌ In Odoo 17, this targets dropdown items, not the delete button!
```

### After (Fixed):
```python
async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
    # Odoo 17: Delete is in the action menu, not a direct button
    action_btn = self.page.locator(".o_cp_action_menus button").first
    await action_btn.click()
    await self.wait.for_ajax()
    
    # Find and click "Delete" text in dropdown
    delete_item = self.page.get_by_text("Delete", exact=True)
    await delete_item.click()
    
    if confirm:
        self.page.on("dialog", lambda dialog: dialog.accept())
        await self.wait.for_all()
```

---

## Running CI/CD

### Add to GitHub Actions
```yaml
name: Test Odoo 17
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: pip install pytest pytest-asyncio playwright
      - run: pytest tests/test_verify_odoo17_functions.py
```

---

## Resources

- [Selectors Reference](src/odoo_playwright/selectors.py) - Version-specific CSS selectors
- [Issue Details](ODOO17_FIXES_NEEDED.md) - Specific fixes needed
- [Odoo 17 Migration Guide](https://www.odoo.com/documentation/17.0/)
- [Playwright Docs](https://playwright.dev/python/)

---

## Tips for Success

✅ **DO**:
- Run tests with `HEADLESS=false` to see what's happening
- Add `SLOW_MO=500` to slow down actions for debugging
- Use `pytest -vvs` to see detailed output
- Test one function at a time to isolate issues

❌ **DON'T**:
- Skip the visual verification step
- Assume selectors work without testing
- Change selectors without testing both Odoo 16 and 17
- Commit fixes without running full test suite

---

## Help & Questions

If tests fail:

1. Check the test output for specific selector errors
2. Review `ODOO17_FIXES_NEEDED.md` for known issues
3. Use browser console to verify selectors exist
4. Run with `HEADLESS=false SLOW_MO=1000` for visual debugging
