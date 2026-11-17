# Odoo 17 AsyncOdooUI Fixes - Progress Checklist

## Pre-Flight Checks

- [ ] Clone/update repository
- [ ] Install dependencies: `pip install -e . && pip install pytest pytest-asyncio playwright`
- [ ] Set ODOO_URL environment variable
- [ ] Set ODOO_USER environment variable
- [ ] Set ODOO_PASSWORD environment variable
- [ ] Verify Odoo instance is reachable: `curl -I $ODOO_URL/web`
- [ ] Test credentials manually in browser

## Initial Test Run

- [ ] Run baseline tests: `./run_odoo17_tests.sh quick`
- [ ] Document initial failure count
- [ ] Review `ODOO17_FIXES_NEEDED.md`
- [ ] Understand each issue before fixing

## Critical Fixes (Fix These First)

### 1. Fix `click_delete()` 🔴
**File**: `src/odoo_playwright/ui_async.py` (lines 299-304)
**Issue**: Delete button selector is wrong in Odoo 17
**Status**: ❌ BROKEN

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Open browser and inspect action menu
- [ ] Verify `.o_cp_action_menus button` exists
- [ ] Update selector to find Delete dropdown item
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs`
- [ ] Verify: Test passes ✅
- [ ] Check: No other tests broken
- [ ] Commit: `git add -p && git commit -m "Fix: click_delete() for Odoo 17 action menu"`

**Fix Template**:
```python
async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
    # Click action menu (gear icon)
    action_menu = self.page.locator(".o_cp_action_menus button").first
    await action_menu.click()
    await self.wait.for_ajax()
    
    # Find and click "Delete" in dropdown
    delete_item = self.page.get_by_text("Delete", exact=True)
    await delete_item.click()
    
    if confirm:
        self.page.on("dialog", lambda dialog: dialog.accept())
        await self.wait.for_all()
```

### 2. Fix `fill_many2one()` 🔴
**File**: `src/odoo_playwright/ui_async.py` (lines 349-368)
**Issue**: Dropdown selector uses deprecated `.ui-autocomplete`
**Status**: ⚠️ PARTIALLY BROKEN

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Inspect many2one field dropdown in browser
- [ ] Verify `.o_dropdown_menu` is the correct selector
- [ ] Update to prioritize new selectors
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_fill_many2one -vvs`
- [ ] Verify: Test passes ✅
- [ ] Check: No other tests broken
- [ ] Commit: `git add -p && git commit -m "Fix: fill_many2one() dropdown selectors for Odoo 17"`

**Key Changes**:
- Prioritize `.o_dropdown_menu` over `.ui-autocomplete`
- Use proper visibility selector
- Handle both old and new selectors as fallback

---

## High Priority Fixes

### 3. Fix `close_modal()` 🟠
**File**: `src/odoo_playwright/ui_async.py` (lines 435-441)
**Issue**: Button selectors too generic
**Status**: ⚠️ PARTIALLY BROKEN

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Create test modal (e.g., open a dialog)
- [ ] Inspect button HTML structure in DevTools
- [ ] Update selectors to be more specific
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Modals::test_close_modal -vvs`
- [ ] Verify: Test passes ✅
- [ ] Check: No regressions
- [ ] Commit: `git add -p && git commit -m "Fix: close_modal() button selectors"`

**Key Changes**:
- Use more specific CSS selectors
- Handle both button[name] and text-based matching
- Fallback to position-based selection (.modal-footer button)

### 4. Fix `get_field_value()` - Select handling 🟠
**File**: `src/odoo_playwright/ui_async.py` (lines 278-289)
**Issue**: `option:checked` may fail on custom select elements
**Status**: ⚠️ WEAK

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Test with form that has select field
- [ ] Check if `option:checked` works
- [ ] Add fallback for custom selects
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_get_field_value_text -vvs`
- [ ] Verify: Test passes ✅
- [ ] Commit: `git add -p && git commit -m "Improve: get_field_value() select handling"`

---

## Medium Priority Fixes

### 5. Improve `fill_field()` - Many2one detection 🟡
**File**: `src/odoo_playwright/ui_async.py` (lines 329-335)
**Issue**: Many2one detection checks only parent, not ancestors
**Status**: ⚠️ WEAK

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Test with many2one field
- [ ] Check ancestor chain for many2one class
- [ ] Update detection logic
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_fill_many2one_field -vvs`
- [ ] Verify: Test passes ✅
- [ ] Commit: `git add -p && git commit -m "Improve: fill_field() many2one detection"`

### 6. Fix `go_to_tab()` - Bootstrap 5 selectors 🟡
**File**: `src/odoo_playwright/ui_async.py` (lines 321-325)
**Issue**: Selector doesn't match Odoo 17's Bootstrap 5 structure
**Status**: ⚠️ INCOMPLETE

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Open a form with tabs
- [ ] Inspect tab HTML in DevTools
- [ ] Update selectors for `.o_notebook .nav-link`
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_TabOperations::test_go_to_tab -vvs`
- [ ] Verify: Test passes ✅
- [ ] Commit: `git add -p && git commit -m "Fix: go_to_tab() Bootstrap 5 selectors"`

---

## Low Priority Fixes

### 7. Improve `search()` - Visibility check 🟢
**File**: `src/odoo_playwright/ui_async.py` (lines 311-317)
**Issue**: No check if search input is visible before typing
**Status**: ⚠️ MINOR

- [ ] Read issue in `ODOO17_FIXES_NEEDED.md`
- [ ] Test search in list view
- [ ] Add wait for search input visibility
- [ ] Test: `pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_SearchAndFilter::test_search_in_list_view -vvs`
- [ ] Verify: Test passes ✅
- [ ] Commit: `git add -p && git commit -m "Improve: search() visibility check"`

---

## Testing After Each Fix

### Template for Each Fix
```bash
# After editing ui_async.py:

# 1. Test the specific fixed function
HEADLESS=false SLOW_MO=500 \
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_CLASSNAME::test_FUNCTIONNAME -vvs

# 2. If it passes, run full test group
./run_odoo17_tests.sh GROUPNAME

# 3. If all pass, run full suite to check regressions
./run_odoo17_tests.sh all

# 4. Commit only if all tests pass
git diff src/odoo_playwright/ui_async.py  # Review changes
git add -p  # Stage specific lines
git commit -m "Fix: descriptive message"
```

---

## Final Verification

- [ ] All fixes committed with clear commit messages
- [ ] Full test suite passes: `./run_odoo17_tests.sh all`
- [ ] No regressions in existing tests
- [ ] Code review (if working with team)
- [ ] Update CHANGELOG if applicable
- [ ] Push to remote: `git push`

## Summary Reporting

### Before Fixes
```
TOTAL TESTS: 70
PASSING: ~38 (54%)
FAILING: ~32 (46%)
```

### After Fixes
```
TOTAL TESTS: 70
PASSING: 70 (100%)
FAILING: 0 (0%)
```

---

## Progress Tracking

### Week 1
- [ ] Day 1: Setup & understand issues
- [ ] Day 2: Fix critical issues (click_delete, fill_many2one)
- [ ] Day 3: Fix high-priority issues (close_modal, get_field_value)
- [ ] Day 4: Fix medium-priority issues
- [ ] Day 5: Verify all fixes, write summary

### Daily Checklist
- [ ] Set environment variables
- [ ] Run current test group
- [ ] Make one fix
- [ ] Test the fix
- [ ] Commit if passing
- [ ] Record progress

---

## Resources

- **Issues**: `ODOO17_FIXES_NEEDED.md` - Full analysis of each problem
- **Testing**: `TESTING_ODOO17.md` - Complete testing guide
- **Quick Ref**: `QUICK_TEST_GUIDE.md` - Common commands
- **Code**: `src/odoo_playwright/ui_async.py` - Code to fix
- **Tests**: `tests/test_verify_odoo17_functions.py` - Test suite

---

## Notes

```
Total fixes needed: 7 functions
Estimated fix time: 2-3 hours
Test time per fix: 5-10 minutes
```

Record any issues/blockers below:

---

## Issues Encountered

### Issue 1: [Description]
- [ ] Resolved
- [ ] Workaround applied
- [ ] Escalated

### Issue 2: [Description]
- [ ] Resolved
- [ ] Workaround applied
- [ ] Escalated

---

## Sign-Off

**Started**: ________________
**Completed**: ________________
**Verified By**: ________________
**Notes**: ________________________________________________
