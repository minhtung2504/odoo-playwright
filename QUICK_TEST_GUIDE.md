# Quick Test Guide - Odoo 17 AsyncOdooUI Verification

## 1. Setup (2 minutes)

```bash
cd /Users/mac/Documents/Code/odoo-playwright

# Install dependencies (if not done)
pip install -e .
pip install pytest pytest-asyncio

# Set environment
export ODOO_URL="https://integration.cc1.vn"
export ODOO_USER="your_username"
export ODOO_PASSWORD="your_password"
export ODOO_DB="your_database"
export HEADLESS=false
export SLOW_MO=500
```

## 2. Run Tests

### Option A: Easy Script (Recommended)
```bash
# Quick smoke test
./run_odoo17_tests.sh quick

# Test form operations  
./run_odoo17_tests.sh forms

# Test all
./run_odoo17_tests.sh all
```

### Option B: Direct pytest
```bash
# Run one test class
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions -v

# Run one test
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs

# Run with output
pytest tests/test_verify_odoo17_functions.py -v -s

# Stop on first failure
pytest tests/test_verify_odoo17_functions.py -x
```

## 3. Review Results

The test output shows which functions work ✅ and which need fixing ❌.

### Tests That Should Pass ✅
- Navigation (URLs, fragments)
- Menu/App navigation  
- List view (rows, search, pagination)
- Kanban view (cards)
- Notifications
- Field reading/writing (mostly)
- Utilities (JS execution, screenshots)

### Tests That May Fail ❌ (Known Issues)
1. **`test_click_delete`** - Delete button moved to action menu in Odoo 17
2. **`test_fill_many2one`** - Dropdown selector needs update
3. **`test_close_modal`** - Button selectors too generic
4. **`test_go_to_tab`** - Bootstrap 5 structure changed

## 4. Understanding Failures

When a test fails, you'll see:

```
FAILED tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete
```

### What this means:
- The `click_delete()` function doesn't work in Odoo 17
- See `ODOO17_FIXES_NEEDED.md` for the specific issue
- Selector for delete button changed in Odoo 17

### How to debug:
```bash
# Run with browser visible to see what's happening
HEADLESS=false SLOW_MO=2000 pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs
```

## 5. Fixing Issues

For each failed test:

1. **Read** the issue in `ODOO17_FIXES_NEEDED.md`
2. **Inspect** the element in browser using DevTools
3. **Update** the selector/code in `src/odoo_playwright/ui_async.py`
4. **Test** the single function: `pytest ... -vvs`
5. **Verify** the fix doesn't break other tests

### Example: Fix `click_delete()`

**Issue**: Delete button selector is wrong in Odoo 17

**Diagnosis**:
```bash
# Run and watch browser
HEADLESS=false SLOW_MO=2000 pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs

# You'll see it tries to click wrong button
```

**Inspect in browser console**:
```javascript
// What exists?
console.log("Delete buttons:", document.querySelectorAll(".o_form_button_delete").length);
console.log("Action menu buttons:", document.querySelectorAll(".o_cp_action_menus button").length);
console.log("Delete in dropdown:", document.textContent.includes("Delete"));
```

**Fix in code**:
```python
# Edit src/odoo_playwright/ui_async.py, find click_delete method
async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
    # Click the action menu (gear icon)
    await self.page.locator(".o_cp_action_menus button").click()
    await self.wait.for_ajax()
    
    # Find and click "Delete" in dropdown
    await self.page.get_by_text("Delete", exact=True).click()
    
    if confirm:
        self.page.on("dialog", lambda dialog: dialog.accept())
        await self.wait.for_all()
```

**Verify**:
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs
```

## 6. Key Test Groups

### Navigation (Basic - Should All Pass)
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Navigation -v
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_AppNavigation -v
```

### Forms (Medium - Some May Fail)
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions -v
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations -v
```

### Lists (Should Pass)
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_ListViewOperations -v
```

### Problem Areas (Will Fail)
```bash
# These test functions that definitely need fixes
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_fill_many2one -vvs
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Modals::test_close_modal -vvs
```

## 7. Before/After Checklist

### Before Running Tests
- [ ] Environment variables set
- [ ] You can access Odoo 17 instance
- [ ] Browser can reach the URL
- [ ] You have valid credentials

### After Running Tests  
- [ ] Note which tests fail
- [ ] Read `ODOO17_FIXES_NEEDED.md`
- [ ] Fix high-priority issues first
- [ ] Rerun tests after each fix
- [ ] Verify no regressions

### Success Indicators
- [ ] `test_navigate_to_path` passes
- [ ] `test_go_to_app_via_command_palette` passes
- [ ] `test_get_list_row_count` passes
- [ ] `test_fill_text_field` passes
- [ ] Navigation tests all pass ✅

## 8. Common Issues & Solutions

### "Timeout waiting for selector"
- Browser can't find the element
- Check selector is correct in `selectors.py`
- Run with `HEADLESS=false` to see what's on screen
- Use DevTools to find correct selector

### "Element is disabled/not visible"
- Element exists but not clickable
- Wait for page load: `await async_odoo_ui.wait.for_all()`
- Scroll element into view first
- Check z-index isn't hiding it

### "Modal won't close"
- Wrong button selector
- Button might not be visible yet
- Try more specific selector
- Check modal structure in DevTools

### "Many2one dropdown doesn't appear"
- `.ui-autocomplete` changed to `.o_dropdown_menu` in Odoo 17
- Update selector in `fill_many2one()`
- Wait for correct selector to appear

## 9. Visual Debugging Mode

For maximum visibility while debugging:

```bash
# Show browser, slow down, see all details
HEADLESS=false SLOW_MO=2000 pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs 2>&1 | tee test_debug.log
```

Tips:
- Watch the browser as test runs
- Pause with `await async_odoo_ui.page.pause()`
- Open DevTools (F12) to inspect
- Check console for JS errors
- Verify selectors in console

## 10. Next Steps

1. **Run quick tests first** to see overall status
2. **Focus on HIGH priority fixes** (see ODOO17_FIXES_NEEDED.md)
3. **Test each fix individually** with `-vvs`
4. **Run full suite** to check for regressions
5. **Commit fixes** when all tests pass

---

## Files Reference

| File | Purpose |
|------|---------|
| `test_verify_odoo17_functions.py` | Main test suite - 70+ tests |
| `ODOO17_FIXES_NEEDED.md` | Detailed analysis of issues and fixes |
| `TESTING_ODOO17.md` | Full guide and documentation |
| `run_odoo17_tests.sh` | Easy test runner script |
| `src/odoo_playwright/ui_async.py` | Code to fix |
| `src/odoo_playwright/selectors.py` | Selectors for Odoo 17 |

---

## Success Example

```bash
# Setup
export ODOO_URL="https://integration.cc1.vn"
export ODOO_USER="admin"
export ODOO_PASSWORD="password"
export HEADLESS=false

# Run quick validation
./run_odoo17_tests.sh quick
# Should see:
# ✅ test_navigate_to_path PASSED
# ✅ test_get_current_model PASSED
# ...

# Now fix issues
# Edit src/odoo_playwright/ui_async.py

# Verify fixes
./run_odoo17_tests.sh all
# Should see all tests passing
```

That's it! You now have a test framework to verify and fix each function.
