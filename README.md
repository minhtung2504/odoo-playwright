# Odoo Playwright

Bộ công cụ điều khiển giao diện Odoo bằng [Playwright](https://playwright.dev/python/), dùng để viết test tự động (E2E) cho Odoo 16, 17, 18 và 19.

Repo gồm 3 phần:

1. **Thư viện `odoo_playwright`**: các lớp `OdooUI`, `FormView`, `ListView`, `KanbanView`, `OdooPage`. Mỗi lớp có bản sync và async, dùng selector riêng cho từng phiên bản Odoo.
2. **Bộ test** trong `tests/`. Bộ chính kiểm tra giao diện Odoo 17. Ngoài ra có các test nghiệp vụ, nổi bật là **tạo PO từ hóa đơn PDF của nhà cung cấp → nhập kho → tạo hóa đơn mua hàng**.
3. **MCP server** (`odoo-playwright-mcp`) để coding agent (Claude Code…) tự sinh và chạy test.

## Mục lục

- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Cài đặt](#cài-đặt)
- [Cấu hình kết nối Odoo](#cấu-hình-kết-nối-odoo)
- [Chạy test](#chạy-test)
- [Tạo đơn mua hàng từ hóa đơn PDF](#tạo-đơn-mua-hàng-từ-hóa-đơn-pdf-của-nhà-cung-cấp)
- [Dùng thư viện](#dùng-thư-viện)
- [API Reference](#api-reference)
- [MCP server cho coding agent](#mcp-server-cho-coding-agent)
- [Phát triển](#phát-triển)
- [Lưu ý](#lưu-ý)

## Cấu trúc thư mục

```
odoo-playwright/
├── src/odoo_playwright/          ← thư viện
│   ├── ui.py / ui_async.py           OdooUI / AsyncOdooUI: đối tượng gốc
│   ├── views.py / views_async.py     FormView, ListView, KanbanView (+ bản Async)
│   ├── page.py / page_async.py       OdooPage, OdooSubMenu (+ bản Async)
│   ├── wait.py                       WaitHelper / AsyncWaitHelper
│   ├── selectors.py                  selector theo phiên bản Odoo 16–19
│   ├── testcase.py                   OdooTestCase, AsyncOdooTestCase, OdooConfig
│   └── mcp_server.py                 MCP server
├── tests/
│   ├── conftest.py                   fixture đăng nhập, tùy chọn --invoice / --pay / --stop-at-po
│   ├── test_verify_odoo17_functions.py   bộ test giao diện Odoo 17 (theo class)
│   ├── test_create_po_from_vendor_invoice.py   PDF hóa đơn → PO → nhập kho → hóa đơn
│   ├── vendor_invoice_parser.py      đọc PDF hóa đơn (pdfplumber)
│   ├── po_completion.py              xác nhận PO, nhập kho, tạo hóa đơn, thanh toán
│   ├── test_create_partner.py, test_sale_order.py   test kịch bản
│   ├── test_mcp_server.py            test MCP server (không cần Odoo)
│   ├── data/vendor_invoices/         folder PDF hóa đơn mặc định
│   └── example/                      ví dụ sync và async
├── docs/
│   ├── scm/                          nghiệp vụ cung ứng: quy trình, test case, OCR hóa đơn
│   └── odoo17-testing/               hướng dẫn và checklist bộ test Odoo 17
├── scripts/                          run_odoo17_tests.sh, test_runner.py
├── skills/                           playwright-mcp.skill (không thuộc package)
├── screenshots/                      ảnh chụp khi test lỗi (gitignored)
└── pyproject.toml, pytest.ini, CLAUDE.md, LICENSE, MANIFEST.in
```

## Cài đặt

Yêu cầu Python ≥ 3.9. Cài từ source ở chế độ editable:

```bash
git clone <repo-url> odoo-playwright
cd odoo-playwright
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"          # thư viện + pytest, ruff, mypy
pip install -e ".[pdf]"          # thêm pdfplumber (test tạo PO từ hóa đơn PDF)
pip install -e ".[mcp]"          # thêm MCP server (tùy chọn)
playwright install chromium
```

Có thể cài một lần: `pip install -e ".[dev,pdf,mcp]"`.

## Cấu hình kết nối Odoo

Mọi test UI cần **một Odoo đang chạy**. Cấu hình bằng biến môi trường. File `.env` **không** được đọc tự động, nên phải export trong shell:

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `ODOO_URL` | `http://localhost:8069` | Địa chỉ Odoo |
| `ODOO_USER` | `admin` | Tài khoản đăng nhập |
| `ODOO_PASSWORD` | `admin` | Mật khẩu |
| `ODOO_DB` | `test` | Tên database |
| `ODOO_VERSION` | `17` | Phiên bản Odoo (chọn bộ selector) |
| `HEADLESS` | `true` | `false` để xem trình duyệt thao tác |
| `SLOW_MO` | `0` | Làm chậm mỗi thao tác (ms), ví dụ `500` |
| `VENDOR_INVOICE_PATH` | (trống) | Đường dẫn PDF hóa đơn cho test tạo PO |

```powershell
# PowerShell
$env:ODOO_URL="https://your-odoo"; $env:ODOO_USER="admin"; $env:ODOO_PASSWORD="..."
$env:ODOO_DB="test"; $env:ODOO_VERSION="17"; $env:HEADLESS="false"
```

```bash
# bash
export ODOO_URL=https://your-odoo ODOO_USER=admin ODOO_PASSWORD=... ODOO_DB=test ODOO_VERSION=17 HEADLESS=false
```

## Chạy test

```bash
pytest                                              # toàn bộ tests/
pytest -m "not integration"                         # chỉ test không cần Odoo
pytest tests/test_verify_odoo17_functions.py        # bộ test giao diện Odoo 17
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions                  # một class
pytest tests/test_verify_odoo17_functions.py::TestAsyncOdooUI_FormActions::test_click_save # một test
pytest -vvs -x                                      # log chi tiết, dừng ở lỗi đầu tiên
```

Chạy theo nhóm bằng script (cả hai đều hardcode các nhóm test Odoo 17):

```bash
python scripts/test_runner.py list                  # liệt kê nhóm
python scripts/test_runner.py all                   # chạy tất cả, có báo cáo test_report.json
python scripts/test_runner.py Navigation            # một nhóm
./scripts/run_odoo17_tests.sh quick | forms | list | modals | all   # chỉ chạy được trên bash
```

Trên terminal Windows, nếu `test_runner.py` lỗi `UnicodeEncodeError` khi in emoji, đặt `PYTHONIOENCODING=utf-8` trước khi chạy.

Marker đăng ký trong `pytest.ini`: `integration`, `slow`, `smoke`, `async`, `fix_needed`. Repo dùng `--strict-markers`, nên marker mới phải được khai báo ở đó trước khi dùng.

Chi tiết về bộ test Odoo 17 nằm trong [`docs/odoo17-testing/`](docs/odoo17-testing/), bắt đầu từ `README_TEST_SUITE.md`.

## Tạo đơn mua hàng từ hóa đơn PDF của nhà cung cấp

Test `tests/test_create_po_from_vendor_invoice.py` đọc hóa đơn PDF của nhà cung cấp và tự làm trên giao diện Odoo 17: tạo RFQ → xác nhận thành PO → nhập kho → tạo hóa đơn mua hàng (và thanh toán nếu muốn).

### Chuẩn bị

1. Cài `pdfplumber`: `pip install -e ".[pdf]"`.
2. Đặt biến môi trường kết nối Odoo ([xem trên](#cấu-hình-kết-nối-odoo)).
3. **Nhà cung cấp và sản phẩm trên hóa đơn phải có sẵn trong Odoo.** Test không tạo dữ liệu gốc. Thiếu nhà cung cấp hoặc sản phẩm thì test báo lỗi.
4. Dùng **database test**: các PO, phiếu nhập kho và hóa đơn tạo ra sẽ được giữ lại trong database.

### Yêu cầu với file PDF

- Phải là PDF dạng text (xuất từ phần mềm hóa đơn điện tử). Test không đọc được PDF scan hay chụp ảnh.
- Có nhãn nhà cung cấp, ví dụ "Đơn vị bán", "Người bán", "Seller" hoặc "Vendor".
- Có bảng hàng hóa với cột tên hàng, số lượng và đơn giá ("Tên hàng", "Số lượng", "Đơn giá"…). Cột "Thành tiền" và "Thuế suất" là không bắt buộc.
- Nên có số hóa đơn, ký hiệu, ngày ("Ngày 12 tháng 10 năm 2026" hoặc "12/10/2026"), thuế suất, cộng tiền hàng và tổng cộng.

Trước khi mở Odoo, test kiểm tra PDF đã được đọc đủ: số lượng × đơn giá phải bằng thành tiền của từng dòng, và tổng các dòng phải bằng cộng tiền hàng (cho phép lệch 1đ). Nếu không khớp, test dừng và báo tên file. Khi đó thường phải bổ sung từ khóa trong `VENDOR_LABELS` hoặc `COLUMN_KEYWORDS` ở `tests/vendor_invoice_parser.py`.

### Chạy

Có 4 cách chỉ định hóa đơn, theo thứ tự ưu tiên:

```bash
# 1. Tham số --invoice: một file, một folder, hoặc lặp lại nhiều lần
pytest tests/test_create_po_from_vendor_invoice.py --invoice "D:\HoaDon\thang10"
pytest tests/test_create_po_from_vendor_invoice.py --invoice a.pdf --invoice b.pdf

# 2. Biến môi trường VENDOR_INVOICE_PATH (nhiều đường dẫn cách nhau bằng ';')
VENDOR_INVOICE_PATH="a.pdf;D:\HoaDon\thang10" pytest tests/test_create_po_from_vendor_invoice.py

# 3. Không truyền gì: test hỏi đường dẫn trên terminal (dán được đường dẫn có dấu ngoặc kép
#    từ "Copy as path" của Windows; để trống rồi Enter để hủy)
pytest tests/test_create_po_from_vendor_invoice.py

# 4. Không trả lời ở bước 3: test dùng các file *.pdf trong tests/data/vendor_invoices/
```

| Tùy chọn | Ý nghĩa |
|----------|---------|
| `--stop-at-po` | Dừng sau khi xác nhận PO, không nhập kho, không tạo hóa đơn |
| `--pay` | Thanh toán toàn bộ hóa đơn mua hàng sau khi vào sổ |
| `-s` | Hiện log chi tiết từng bước (PO, phiếu nhập kho, hóa đơn) |

Ví dụ: `pytest tests/test_create_po_from_vendor_invoice.py --invoice "D:\HoaDon" --pay -s`

### Cách test xử lý một folder nhiều hóa đơn

1. **Gom theo nhà cung cấp:** các hóa đơn cùng nhà cung cấp vào **1 PO**, nhà cung cấp khác thì tạo PO riêng. Tên nhà cung cấp phải giống hệt nhau giữa các PDF (chỉ bỏ qua khác biệt hoa/thường và khoảng trắng). Nếu tên viết khác đi, các hóa đơn sẽ bị tách thành nhiều PO.
2. **Sắp xếp:** trong mỗi PO, hóa đơn được xử lý theo **ngày hóa đơn, cũ nhất trước**, vì Odoo không cho tạo hóa đơn có ngày trước ngày nhập kho. Hóa đơn không đọc được ngày xếp cuối.
3. **Nhập kho và tạo hóa đơn theo từng PDF:** với mỗi hóa đơn PDF:
   - nhập kho đúng số lượng của hóa đơn đó, ngày nhập kho bằng ngày hóa đơn; phần còn lại chuyển sang đơn hàng chờ (backorder) cho các hóa đơn sau;
   - tạo hóa đơn mua hàng **chỉ từ phiếu nhập kho vừa tạo**, mang số hóa đơn, ký hiệu và ngày của PDF đó.
4. **Đối chiếu:** mỗi hóa đơn trên Odoo phải ở trạng thái đã vào sổ, với tiền trước thuế và tổng tiền khớp PDF tương ứng.

Folder chỉ có 1 hóa đơn thì test nhập kho toàn bộ rồi tạo 1 hóa đơn.

```
Folder: A1.pdf, A2.pdf (nhà cung cấp A), B.pdf (nhà cung cấp B)

PO A: dòng của A1 + A2 → Nhập kho 1 + Hóa đơn A1 → Nhập kho 2 (backorder) + Hóa đơn A2
PO B: dòng của B       → Nhập kho + Hóa đơn B
```

Mỗi bước trong `tests/po_completion.py` đều kiểm tra trạng thái thật của PO qua JSON-RPC trước khi làm, và bỏ qua phần đã xong. Vì vậy nếu chạy lại trên cùng một PO, test sẽ làm tiếp từ chỗ dừng thay vì tạo thêm phiếu nhập kho hay hóa đơn.

### Khi test lỗi

- Log in ra trạng thái trang tại thời điểm lỗi (chạy với `-s` để xem).
- Ảnh chụp màn hình được lưu trong thư mục `screenshots/`.
- Lỗi thường gặp:
  - thiếu nhà cung cấp hoặc sản phẩm trong Odoo;
  - tên trên PDF không khớp tên trong Odoo;
  - PDF có bố cục hoặc nhãn lạ, nên không đọc được dòng hàng;
  - Odoo từ chối lưu vì còn trường bắt buộc trống.

## Dùng thư viện

### Sync

```python
from playwright.sync_api import sync_playwright
from odoo_playwright import OdooUI

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    ui = OdooUI(page, base_url="http://localhost:8069", version=17)
    ui.login("admin", "admin", "mydb")

    ui.go_to_app("Contacts")
    ui.click_create()
    ui.fill_field("name", "My New Partner")
    ui.click_save()

    browser.close()
```

### Async

```python
from playwright.async_api import async_playwright
from odoo_playwright.ui_async import AsyncOdooUI

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        ui = AsyncOdooUI(page, base_url="http://localhost:8069", version=17)
        await ui.login("admin", "admin", "mydb")

        await ui.go_to_app("Contacts")
        await ui.click_create()
        await ui.fill_field("name", "My New Partner")
        await ui.click_save()

        await browser.close()
```

### Với pytest

`tests/conftest.py` có sẵn các fixture. Fixture `odoo_ui` / `async_odoo_ui` đã đăng nhập trước khi test chạy.

| Fixture | Mô tả |
|---------|-------|
| `odoo_ui` | `OdooUI` (sync) đã đăng nhập |
| `async_odoo_ui` | `AsyncOdooUI` đã đăng nhập (pytest-asyncio, `asyncio_mode = auto`) |
| `odoo_config` | `OdooConfig` đọc từ biến môi trường |
| `odoo_page` | `OdooPage` từ `odoo_ui` |
| `page`, `context`, `browser` | Đối tượng Playwright (browser dùng chung cả session) |
| `screenshot_on_failure` | Tự chụp màn hình khi test lỗi |

```python
async def test_create_partner(async_odoo_ui):
    await async_odoo_ui.go_to_app("Contacts")
    await async_odoo_ui.click_create()
    await async_odoo_ui.fill_field("name", "Test Partner")
    await async_odoo_ui.click_save()

    notification = await async_odoo_ui.wait_for_notification()
    assert notification is None or notification["type"] == "success"
```

Có thể dùng class `OdooTestCase` / `AsyncOdooTestCase` (`odoo_playwright.testcase`) thay cho fixture. Ví dụ dùng fixture có trong `tests/example/` (`test_odoo_basic.py` cho sync, `test_odoo_async.py` cho async).

### Page object và view

```python
from odoo_playwright import OdooPage
from odoo_playwright.views import FormView, KanbanView, ListView

# Trang ứng dụng + menu. Dùng OdooPage(ui, ...), không dùng ui.page(...): xem phần Lưu ý
OdooPage(ui, "Sales").navigate().menu("Orders", "Quotations")

# List view
list_view = ListView(ui, "res.partner")
list_view.search("My Partner")
form = list_view.click_row_by_value("name", "My Partner")   # trả về FormView
rows = list_view.get_values(["name", "email"])
list_view.select_rows_by_value("name", "Test Partner")
list_view.delete_selected()
list_view.pager_next()
info = list_view.get_pager_info()                            # {'from', 'to', 'total'}

# Form view
form = FormView(ui, "res.partner")
form.create(name="John Doe", email="john@example.com")
form.go_to_tab("Sales & Purchase")
form.add_one2many_item("child_ids")
form.upload_file("image_1920", "/path/to/image.png")
form.save()

# Kanban view
kanban = KanbanView(ui, "project.task")
kanban.get_card_count()
kanban.open_card(0)
kanban.quick_create(column_name="To Do", name="New Task")
kanban.move_card_to_column("My Task", "In Progress")
```

Bản async có tên giống hệt: `AsyncFormView`, `AsyncListView`, `AsyncKanbanView` trong `odoo_playwright.views_async`, và `AsyncOdooPage` trong `odoo_playwright.page_async`.

### Chờ Odoo xử lý xong

Odoo dùng AJAX và render bất đồng bộ, nên cần chờ trước khi đọc kết quả. `ui.wait` là `WaitHelper` (bản async là `AsyncWaitHelper`):

```python
ui.wait.for_loading()        # chờ hết lớp phủ loading
ui.wait.for_ajax()           # chờ hết request AJAX
ui.wait.for_odoo_ready()     # chờ framework JS của Odoo sẵn sàng
ui.wait.for_all()            # tất cả các bước trên
ui.wait.for_selector(css)    # chờ phần tử xuất hiện (for_selector_hidden: chờ biến mất)
ui.wait.for_text(text)       # chờ một đoạn chữ xuất hiện
ui.wait.for_url(pattern)     # chờ URL khớp mẫu

with ui.expect_ajax():       # context manager: chờ AJAX do thao tác bên trong gây ra
    ui.click_button("action_confirm")
```

### Selector theo phiên bản

`selectors.py` có một dict cho mỗi phiên bản (`SELECTORS_V16` … `SELECTORS_V19`). Phiên bản không có trong danh sách sẽ dùng bộ V17. Hãy lấy selector qua key thay vì viết CSS cứng trong code:

```python
from odoo_playwright.selectors import OdooSelectors, get_selectors

selectors = get_selectors(17)
selectors.get(OdooSelectors.BUTTON_SAVE)
selectors.get(OdooSelectors.LIST_ROW)
# Trong OdooUI: self.selectors.get(...)
```

## API Reference

### OdooUI / AsyncOdooUI

| Nhóm | Phương thức |
|------|-------------|
| Điều hướng | `login(user, password, db)`, `logout()`, `navigate(path)`, `go_to_app(name)`, `go_to_menu(*path)`, `switch_view(type)`, `get_current_model()`, `get_current_view_type()`, `wait_for_url_contains(text)` |
| Nút form | `click_create()`, `click_save()`, `click_edit()`, `click_discard()`, `click_delete(confirm)`, `click_action(name)`, `click_button(name, by_aria_label)` |
| Trường | `get_field(name)`, `get_field_value(name)`, `fill_field(name, value)`, `fill_many2one(name, value)`, `clear_field(name)`, `go_to_tab(name)` |
| Tìm kiếm | `search(query, clear_previous)`, `clear_search()`, `filter_by(name)`, `group_by(field)` |
| List | `get_list_rows()`, `get_list_row_count()`, `get_list_values(columns)`, `click_list_row(i)`, `click_list_row_by_value(col, val)`, `select_list_rows(col, val)`, `select_all_rows()` |
| Phân trang | `pager_next()`, `pager_previous()`, `pager_first()`, `pager_last()`, `get_pager_info()` |
| Kanban | `get_kanban_cards()`, `get_kanban_card_count()`, `open_kanban_card(i)` |
| Dialog & thông báo | `is_modal_open()`, `close_modal(save)`, `confirm_dialog()`, `cancel_dialog()`, `get_notification()`, `wait_for_notification(timeout)`, `dismiss_notification()` |
| Tiện ích | `take_screenshot(path)`, `expect_ajax()`, `execute_js(script)`, `get_odoo_version()`, `install_module(name, upgrade)`, `view(model, type)` |

### FormView

`create(**fields)`, `fill(**fields)`, `edit()`, `save()`, `discard()`, `delete(confirm)`, `go_to_tab(name)`, `get_status()`, `set_status(name)`, `is_readonly()`, `is_dirty()`, `add_one2many_item(field)`, `remove_one2many_item(field, i)`, `get_one2many_values(field, columns)`, `upload_file(field, path)`, `clear_file(field)`, `open_translations(field)`

### ListView

`create(**fields)`, `get_row_count()`, `get_rows()`, `get_values(columns)`, `click_row(i)`, `click_row_by_value(col, val)`, `select_row(i)`, `select_rows_by_value(col, val)`, `select_all()`, `delete_selected()`, `pager_next()`, `pager_previous()`, `get_pager_info()`, `search(...)`, `filter_by(...)`, `group_by(...)`, `is_empty()`, `sort_by(column)`

### KanbanView

`create(**fields)`, `get_card_count()`, `get_cards()`, `open_card(i)`, `get_column_count()`, `get_column_cards(name)`, `move_card_to_column(card, column)`, `quick_create(column_name, **fields)`, `search(...)`, `filter_by(...)`, `group_by(...)`

## MCP server cho coding agent

MCP server chạy cục bộ qua stdio, để agent vừa sửa tính năng Odoo có thể sinh và chạy ngay test hồi quy Playwright. Hãy chạy lệnh từ thư mục repo nơi test sẽ được tạo:

```bash
pip install -e ".[mcp]"
playwright install chromium
odoo-playwright-mcp
```

Ví dụ cấu hình MCP client:

```json
{
  "mcpServers": {
    "odoo-playwright": {
      "command": "odoo-playwright-mcp",
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_USER": "admin",
        "ODOO_PASSWORD": "admin",
        "ODOO_DB": "test",
        "ODOO_VERSION": "17",
        "HEADLESS": "true"
      }
    }
  }
}
```

| Tool | Chức năng |
|------|-----------|
| `get_test_config` | Hiện cấu hình môi trường test Odoo cần có |
| `create_test_template` | Sinh khung test pytest dùng fixture `odoo_ui` |
| `write_test` | Ghi file test; chỉ cho phép `tests/**/test_*.py` trong thư mục hiện tại |
| `run_tests` | Chạy pytest không qua shell và trả về exit code cùng output. Chỉ nhận biến môi trường nằm trong danh sách cho phép (`ALLOWED_ENV_KEYS`) |

## Phát triển

```bash
ruff check .        # lint (line-length 100, rules E,F,I,N,W,UP)
mypy src            # kiểm tra kiểu (Python 3.9)
pytest -m "not integration"   # test nhanh, không cần Odoo
```

- **Sync và async là hai bản viết tay song song** (`ui.py` ↔ `ui_async.py`, `views.py` ↔ `views_async.py`, `page.py` ↔ `page_async.py`, `WaitHelper` ↔ `AsyncWaitHelper`). Sửa hành vi hay selector ở một bản thì sửa cả bản còn lại.
- Thiết lập test sửa trong `pytest.ini`, vì file này được ưu tiên hơn `[tool.pytest.ini_options]` trong `pyproject.toml`.
- Hướng dẫn cho Claude Code nằm trong `CLAUDE.md`.

## Lưu ý

- **`ui.page` là đối tượng Playwright `Page`, không phải phương thức.** Thuộc tính `page` gán trong `__init__` ghi đè phương thức `page(name)`, nên `ui.page("Sales")` không chạy. Hãy dùng `OdooPage(ui, "Sales")` hoặc `AsyncOdooPage(ui, "Sales")`.
- Một số selector V17 chưa được kiểm chứng. Các hàm sau đang biết là lỗi trên Odoo 17:

  | Hàm | Lý do |
  |-----|-------|
  | `click_delete` | nút Xóa đã chuyển vào menu Action |
  | `fill_many2one` | selector dropdown `.ui-autocomplete` đã cũ |
  | `close_modal` | selector nút quá chung chung |
  | `go_to_tab` | cấu trúc tab Bootstrap 5 |

  Xem thêm `docs/odoo17-testing/FIX_CHECKLIST.md`.
- Test nghiệp vụ (tạo PO từ hóa đơn…) được viết cho Odoo 17 tùy biến, nhãn tiếng Việt. Odoo khác có thể cần chỉnh nhãn và selector.

## License

MIT. Lấy cảm hứng từ [odooselenium](https://github.com/meta-it/odooselenium).
