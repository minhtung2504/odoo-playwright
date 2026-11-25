# 🔧 Odoo 17 Functions - Summary of Fixes Needed

## 7 Functions Cần Fix

### 1. 🔴 CRITICAL: `click_delete()` - Line 299

**Vấn đề**: Delete button selector sai trong Odoo 17
- Odoo 17 chuyển Delete vào action menu (dropdown)
- Code hiện tại tìm `.o_form_button_delete` (không tồn tại)

**Dấu hiệu**: Test `test_click_delete` fails

**Fix**:
```python
async def click_delete(self, confirm: bool = True, timeout: int = 10000) -> None:
    # Odoo 17: Delete nằm trong action menu dropdown
    action_menu = self.page.locator(".o_cp_action_menus button").first
    await action_menu.click()
    await self.wait.for_ajax()
    
    # Tìm và click "Delete" text trong dropdown
    delete_item = self.page.get_by_text("Delete", exact=True)
    await delete_item.click()
    
    if confirm:
        self.page.on("dialog", lambda dialog: dialog.accept())
        await self.wait.for_all()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs
```

---

### 2. 🟠 HIGH: `fill_many2one()` - Line 349

**Vấn đề**: Selector dropdown outdated
- Code dùng `.ui-autocomplete` (jQuery UI, deprecated in Odoo 17)
- Odoo 17 dùng `.o_dropdown_menu`

**Dấu hiệu**: Test `test_fill_many2one` fails, dropdown không hiện

**Fix**:
```python
async def fill_many2one(
    self,
    field_name: str,
    value: str,
    create_if_not_found: bool = False,
    search_more: bool = False,
) -> None:
    field = self.get_field(field_name)
    await field.click()

    input_elem = field.locator("input").first
    await input_elem.fill(value)

    # Odoo 17: .o_dropdown_menu trước, rồi fallback .ui-autocomplete
    try:
        await self.page.wait_for_selector(".o_dropdown_menu:visible, .ui-autocomplete:visible", timeout=5000)
    except:
        raise TimeoutError(f"Dropdown not found for many2one field '{field_name}'")

    if search_more:
        await self.page.get_by_text("Search More...").click()
        await self.wait.for_all()
        await self.page.locator(".o_list_view").get_by_text(value, exact=True).first.click()
    elif create_if_not_found:
        await self.page.get_by_text("Create and Edit...").click()
        await self.wait.for_all()
    else:
        # Tìm item trong dropdown
        dropdown_item = self.page.locator(".o_dropdown_menu, .ui-autocomplete").get_by_text(value, exact=True).first
        if await dropdown_item.count() > 0:
            await dropdown_item.click()
        else:
            await self.page.keyboard.press("Enter")

    await self.wait.for_all()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_fill_many2one -vvs
```

---

### 3. 🟠 HIGH: `close_modal()` - Line 435

**Vấn đề**: Button selectors quá generic
- `.btn-primary` không đủ specific
- Có thể click sai button

**Dấu hiệu**: Test `test_close_modal` fails, modal không close

**Fix**:
```python
async def close_modal(self, save: bool = False) -> None:
    modal = self.page.locator(self.selectors.get("modal"))

    if save:
        # Tìm save button cụ thể hơn
        save_btn = modal.locator(
            "button[name='save'], button.btn-primary:has-text('Save'), "
            ".modal-footer button:last-child"
        ).first
        if await save_btn.count() > 0:
            await save_btn.click()
    else:
        # Tìm cancel button cụ thể hơn
        cancel_btn = modal.locator(
            "button[name='cancel'], button.btn-secondary:has-text('Cancel'), "
            ".modal-footer button:first-child, .close"
        ).first
        if await cancel_btn.count() > 0:
            await cancel_btn.click()

    await self.wait.for_all()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_Modals::test_close_modal -vvs
```

---

### 4. 🟡 MEDIUM: `get_field_value()` - Line 278

**Vấn đề**: `option:checked` không work với custom select fields

**Dấu hiệu**: Không thể đọc giá trị từ select field

**Fix**:
```python
async def get_field_value(self, field_name: str) -> str:
    field = self.get_field(field_name)

    tag = await field.evaluate("el => el.tagName.toLowerCase()")
    input_type = await field.get_attribute("type") or ""

    if tag == "select":
        # Thử standard select trước
        option = field.locator("option:checked").first
        if await option.count() > 0:
            return await option.inner_text()
        # Fallback cho custom select
        selected_value = await field.get_attribute("data-value")
        return selected_value or ""
    elif input_type == "checkbox":
        return str(await field.is_checked())
    elif tag == "input" or tag == "textarea":
        return await field.input_value()
    else:
        return await field.inner_text()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_get_field_value_text -vvs
```

---

### 5. 🟡 MEDIUM: `fill_field()` - Line 329

**Vấn đề**: Many2one detection chỉ check parent, không check ancestors

**Dấu hiệu**: Many2one field không điền được value

**Fix**:
```python
# Trong fill_field(), thay:
parent_class = await field.evaluate("el => el.parentElement?.className || ''")

# Bằng:
parent_class = await field.evaluate("el => {
    let p = el.parentElement;
    let classes = '';
    while(p && p !== document.body) {
        if(p.className && p.className.includes('many2one')) {
            return 'many2one';
        }
        p = p.parentElement;
    }
    return '';
}")

is_many2one = "many2one" in field_class.lower() or "many2one" in parent_class.lower()
if is_many2one:
    await self.fill_many2one(field_name, str(value))
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FieldOperations::test_fill_many2one_field -vvs
```

---

### 6. 🟡 MEDIUM: `go_to_tab()` - Line 321

**Vấn đề**: Bootstrap 5 đổi cấu trúc tab
- Odoo 17 dùng `.o_notebook .nav-link` (Bootstrap 5)
- Code hiện tại dùng `.o_notebook_tabs .nav-tabs` (cũ)

**Dấu hiệu**: Tab không switch được

**Fix**:
```python
async def go_to_tab(self, tab_name: str) -> None:
    # Cập nhật selector cho Bootstrap 5
    tab = self.page.locator(
        ".o_notebook .nav-link, "
        ".o_notebook_tabs .nav-link, "
        ".nav-tabs .nav-link"
    ).get_by_text(tab_name, exact=True)
    
    await tab.click()
    await self.wait.for_ajax()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_TabOperations::test_go_to_tab -vvs
```

---

### 7. 🟢 LOW: `search()` - Line 311

**Vấn đề**: Không check search input có visible trước khi điền

**Dấu hiệu**: Search input không visible, lỗi timeout

**Fix**:
```python
async def search(self, query: str, clear_previous: bool = True) -> None:
    if clear_previous:
        await self.clear_search()

    # Đảm bảo search input visible
    search_input = self.page.locator(self.selectors.get("search_input"))
    await search_input.wait_for(state="visible", timeout=5000)
    
    await search_input.click()
    await search_input.fill(query)
    await self.page.keyboard.press("Enter")
    await self.wait.for_all()
```

**Kiểm tra**: 
```bash
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_SearchAndFilter::test_search_in_list_view -vvs
```

---

## 📋 Workflow Để Fix

### Cho Mỗi Function:

1. **Đọc Fix** (ở trên)
2. **Chạy Test**:
   ```bash
   HEADLESS=false SLOW_MO=500 pytest tests/test_verify_odoo17_functions.py::TestClass::test_name -vvs
   ```
3. **Inspect HTML** - Mở DevTools (F12) để kiểm tra selector thực tế
4. **Edit Code** - `src/odoo_playwright/ui_async.py`
5. **Test Lại** - Chạy test đó để verify fix
6. **Check Regression** - Chạy full test group để đảm bảo không break cái khác
7. **Commit** - `git add -p && git commit -m "Fix: function_name for Odoo 17"`

### Ví Dụ Cơ Thể:

```bash
# 1. Test fails
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs

# 2. Chạy với browser visible để debug
HEADLESS=false SLOW_MO=1000 pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs

# 3. Inspect HTML trong browser (F12)
# Tìm .o_cp_action_menus button

# 4. Edit code
nano src/odoo_playwright/ui_async.py
# Tìm click_delete method, apply fix

# 5. Test lại
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_delete -vvs

# 6. Test toàn group
./scripts/run_odoo17_tests.sh forms

# 7. Commit
git add src/odoo_playwright/ui_async.py
git commit -m "Fix: click_delete() for Odoo 17 action menu"
```

---

## ⏱️ Ước Tính Time

| Function | Độ Khó | Time |
|----------|--------|------|
| click_delete() | 🟢 Dễ | 10 min |
| fill_many2one() | 🟡 Trung bình | 15 min |
| close_modal() | 🟡 Trung bình | 10 min |
| get_field_value() | 🟢 Dễ | 5 min |
| fill_field() | 🟡 Trung bình | 10 min |
| go_to_tab() | 🟢 Dễ | 5 min |
| search() | 🟢 Dễ | 5 min |
| **TOTAL** | | **60 min (1 hour)** |

---

## ✅ Verification Checklist

Sau khi fix tất cả:

- [ ] click_delete() test passes
- [ ] fill_many2one() test passes
- [ ] close_modal() test passes
- [ ] get_field_value() test passes
- [ ] fill_field() test passes
- [ ] go_to_tab() test passes
- [ ] search() test passes
- [ ] Full test suite passes: `./scripts/run_odoo17_tests.sh all`
- [ ] No regressions in other tests

---

## 📖 Reference

- **HTML Inspector**: Browser DevTools (F12)
- **Selectors để check**: 
  - `.o_cp_action_menus button` - Action menu
  - `.o_dropdown_menu` - Dropdown items
  - `.o_notebook .nav-link` - Tab buttons
  - `.modal-dialog` - Modal
  
- **Test Command**:
  ```bash
  HEADLESS=false SLOW_MO=500 pytest tests/test_verify_odoo17_functions.py::TestClass::test_name -vvs
  ```

---

## 🎯 Prioritization

**Fix Order** (High → Low Priority):
1. `click_delete()` - CRITICAL
2. `fill_many2one()` - HIGH
3. `close_modal()` - HIGH
4. Remaining 4 - MEDIUM/LOW

**Commit strategy**: 1 function = 1 commit (dễ review, dễ rollback)

---

Good luck! 🚀
