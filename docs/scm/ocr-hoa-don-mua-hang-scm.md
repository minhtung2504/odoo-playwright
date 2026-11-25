# Phân tích: Đọc hóa đơn mua hàng bằng OCR (SCM)

**Module:** `xb_purchase_vendor_bill_ocr` (phiên bản 17.0.1.0.1)
**Vị trí mã nguồn:** `pms-scm-frm/xb_purchase_vendor_bill_ocr/`
**Phạm vi:** Tải PDF hóa đơn đầu vào trên đơn mua, dùng ChatGPT đọc nội dung, khớp dòng với đơn mua, rồi tạo phiếu nhập kho và/hoặc hóa đơn nhà cung cấp.

---

## 1. Tổng quan

Module thêm vào đơn mua (`purchase.order`) khả năng nhận hóa đơn PDF của nhà cung cấp. Hệ thống đọc hóa đơn bằng AI, đối chiếu với đơn mua, và để người mua hàng duyệt trước khi tạo chứng từ.

Các đối tượng chính:

| Đối tượng kỹ thuật | Vai trò nghiệp vụ |
|---|---|
| Yêu cầu OCR (`vendor.bill.ocr.request`) | Một lần tải lên một file PDF. Một file có thể chứa nhiều hóa đơn. |
| Hóa đơn đầu vào (`vendor.inbound.bill`) | Một hóa đơn được AI đọc ra. Người dùng duyệt, rồi tạo phiếu nhập hoặc hóa đơn từ đây. |
| Dòng hóa đơn đầu vào (`vendor.inbound.bill.line`) | Một dòng hàng trên hóa đơn, có gán dòng đơn mua tương ứng. |
| Wizard tải PDF (`vendor.bill.ocr.upload.wizard`) | Hộp thoại mở từ đơn mua để tải file. |

---

## 2. Quy trình thực hiện (dành cho người dùng nghiệp vụ)

### Bước 1. Tải hóa đơn PDF lên đơn mua
1. Mở đơn mua đã xác nhận (trạng thái Purchase hoặc Done). Đơn ở trạng thái nháp sẽ bị từ chối.
2. Bấm nút **Inbound Bill (OCR)** ở thanh tiêu đề.
3. Chọn file PDF. Hệ thống chỉ nhận file có đuôi `.pdf`.
4. Bấm xác nhận. Hệ thống báo "OCR request ... has been received and is running in the background" và tạo một yêu cầu OCR ở trạng thái **Queued**.

Chưa có khóa API ChatGPT thì nút này báo lỗi và không mở hộp thoại.

### Bước 2. Chờ hệ thống đọc hóa đơn
- Yêu cầu chuyển sang **Processing**, rồi **Ready** khi xong.
- Trên đơn mua có nút thông kê **OCR Requests** để xem trạng thái từng yêu cầu.
- Trên đơn mua có nút thông kê **Inbound Bills** để xem các hóa đơn đã đọc.
- Khi có hóa đơn chờ duyệt, đơn mua có việc cần làm "OCR bill review" gửi cho người tạo yêu cầu.

### Bước 3. Kiểm tra từng hóa đơn đọc được
Mở từng hóa đơn ở trạng thái **To Review** và kiểm tra:
- Số ký hiệu, số hóa đơn, ngày hóa đơn, loại hóa đơn (bình thường, điều chỉnh, thay thế).
- MST và tên người bán. Hệ thống đã so MST với nhà cung cấp trên đơn mua, nên ở bước này thường đã khớp.
- Tổng tiền chưa thuế, tiền thuế, tổng tiền.
- Từng dòng hàng: tên, mã, số lượng, đơn vị tính, đơn giá, thuế suất.
- Cột khớp: dòng nào đã gán dòng đơn mua, dòng nào chưa khớp.

Sửa được các trường trên hóa đơn ở bước này. Hệ thống không tự kiểm tra tổng dòng có khớp tổng hóa đơn trên PDF hay không, nên cần so tay.

### Bước 4. Khớp dòng với đơn mua
- Dòng đã khớp: kiểm tra đúng dòng đơn mua.
- Dòng chưa khớp: bấm **Match PO** để hệ thống chạy lại việc khớp. Nếu vẫn chưa khớp thì chọn dòng đơn mua bằng tay, hoặc bỏ chọn dòng nếu đó là chi phí không thuộc đơn mua.
- Nhập **số lượng xác nhận** theo đơn vị của đơn mua. Đơn vị trên hóa đơn có thể khác đơn vị đơn mua.

### Bước 5. Duyệt
- Bấm **Approve**: hóa đơn chuyển sang Approved. Hệ thống chặn nếu còn dòng đã chọn chưa khớp, hoặc dòng đã chọn chưa có số lượng xác nhận.
- Bấm **Reject** để loại hóa đơn đọc sai hoặc không cần dùng. Hóa đơn bị loại không còn giữ số lượng đơn mua. Hóa đơn đã Confirmed không loại được.
- Bấm **Reset to Review** để đưa hóa đơn đã loại về To Review.

### Bước 6. Tạo chứng từ
Từ hóa đơn đã Approved, chọn một trong các việc sau:

| Nút | Kết quả | Ghi chú |
|---|---|---|
| **Receive** | Tạo phiếu nhập kho cho các dòng hàng hóa, vật tư đã chọn, theo số lượng xác nhận. | Chỉ tạo một lần. Nếu đã có phiếu thì phải xác nhận hoặc hủy phiếu đó. Hóa đơn chỉ có dịch vụ thì chuyển ngay sang Confirmed, không tạo phiếu. |
| **Create Bill** | Tạo hóa đơn nhà cung cấp (kế toán), thuế lấy theo từng dòng, đính kèm PDF gốc. | Hóa đơn chuyển sang Confirmed. |
| **Create Combined Bill** | Gộp nhiều hóa đơn đã duyệt thành một hóa đơn kế toán. | Dùng khi cùng nhà cung cấp và cần gộp. |

Hóa đơn đã Confirmed thì không loại được.

### Bước 7. Xử lý lỗi
- Yêu cầu ở trạng thái **Error**: đọc thông báo lỗi trong trường Error Message. Lỗi tạm thời (rate limit, mất kết nối) hệ thống đã tự thử lại tối đa 3 lần. Lỗi nghiệp vụ, như MST không khớp hay hóa đơn trùng, cần sửa đơn mua hoặc bỏ hóa đơn trùng rồi tải lại.
- Hàm chạy lại yêu cầu: `action_requeue_ocr` (chưa kiểm tra nút tương ứng trên giao diện).

---

## 3. Luồng kỹ thuật

Các bước dưới đây theo đúng thứ tự gọi trong mã nguồn.

1. **Tải lên.** Wizard `vendor.bill.ocr.upload.wizard` tạo bản ghi `vendor.bill.ocr.request` ở trạng thái `queued` và gọi `action_process_ocr` qua queue_job, cấu hình tối đa 3 lần thử. (`wizard/vendor_bill_ocr_upload.py`)
2. **Kiểm tra quyền.** `action_process_ocr` kiểm tra người dùng có quyền đọc đơn mua. Trạng thái chuyển sang `processing`. (`models/vendor_bill_ocr_request.py:137`)
3. **Chia PDF.** `_split_pages_into_invoice_chunks` (`:607`) tìm trang bắt đầu hóa đơn theo từ khóa tiếng Việt và tiếng Anh, rồi chia thành đoạn tối đa 3 trang. Nếu PDF có lớp văn bản thì gửi chữ; nếu không thì gửi ảnh 150 dpi.
4. **Gọi ChatGPT.** `_call_ai_service` (`:670`) gọi `client.beta.chat.completions.parse` với model từ cấu hình (mặc định `gpt-4o`), nhiệt độ 0, và khuôn dữ liệu Pydantic (`models/vendor_bill_ocr_schema.py`). Nếu lỗi khuôn dữ liệu thì thử lại với `json_object`. Lỗi tạm thời thì ném `RetryableJobError`; lỗi xác thực hoặc yêu cầu sai thì báo lỗi ngay.
5. **Gộp đoạn.** Các đoạn có cùng số ký hiệu và số hóa đơn được gộp. Đoạn không có số thì gộp vào hóa đơn trước đó.
6. **Kiểm tra MST.** Lấy 10 ký tự đầu của MST hóa đơn và MST nhà cung cấp trên đơn mua. Khác nhau thì báo lỗi "Detected invoice MISMATCH". Đơn mua chưa có MST mà hóa đơn có MST thì báo lỗi yêu cầu cập nhật MST cho nhà cung cấp.
7. **Kiểm tra trùng.** Cùng đơn mua, cùng số ký hiệu và số hóa đơn đã có thì báo trùng.
8. **Tìm hóa đơn đã đồng bộ e-invoice.** `_find_synced_einvoice` (`:444`) tìm hóa đơn đã nhập từ nhà cung cấp hóa đơn điện tử. Nếu có, hệ thống gộp dữ liệu OCR vào bản đó (`_merge_into_synced_einvoice`, `:458`), không tạo bản mới. Nếu còn bản OCR cũ chưa duyệt của cùng hóa đơn thì bản đó bị xóa.
9. **Tạo hóa đơn đầu vào.** Ngày không đọc được thì lấy ngày hôm nay. Loại hóa đơn lạ thì coi là `normal`. Tạo `vendor.inbound.bill` ở trạng thái `to_review`, và ghi `provider_invoice_ref` theo mẫu `OCR_<id yêu cầu>_<ký hiệu>_<số>`. Nếu đã có bản ghi cùng khóa thì cập nhật bản đó (không tạo lại).
10. **Tạo dòng.** Dòng không có số lượng, đơn giá, mã và không có số thứ tự là dòng tiêu đề mục. Dòng thường: thuế suất lấy từ dòng hoặc tính từ tiền thuế chia tiền chưa thuế của hóa đơn. Nếu AI gán dòng đơn mua và không có xung đột thông số (`specs_conflict`) thì gán, điểm khớp lấy từ AI hoặc 100.
11. **Khớp dự phòng.** Với dòng chưa khớp, gọi `action_auto_match_po_lines` (`models/vendor_inbound_bill.py:397`). Thứ tự: mã sản phẩm trùng (điểm 100), sau đó chấm điểm mô tả và tên sản phẩm theo `_score_po_line`. Chỉ nhận điểm từ 45 (`MATCH_SCORE_THRESHOLD`, `models/vendor_inbound_bill_line.py:14`). Mỗi dòng đơn mua chỉ gán một lần, trừ khi không còn lựa chọn khác.
12. **Số lượng xác nhận.** Dòng đã khớp: số lượng xác nhận lấy từ số lượng hóa đơn quy đổi sang đơn vị đơn mua (`_po_uom_quantity`).
13. **Đính kèm PDF.** Mỗi hóa đơn có một bản sao PDF, tên `ký hiệu_số.pdf`, đính kèm vào hóa đơn trong chatter.
14. **Duyệt.** `action_approve` (`:341`) chuyển `to_review` → `approved` nếu không có dòng chọn chưa khớp và mọi dòng chọn có số lượng xác nhận lớn hơn 0.
15. **Tạo chứng từ.**
    - `action_create_receipt` (`:454`): chỉ tạo khi chưa có phiếu nhập (trừ phiếu đã hủy). Lấy các dòng chọn, có số lượng xác nhận, có dòng đơn mua, và sản phẩm loại `product` hoặc `consu`. Không có dòng nào thì chuyển thẳng sang `confirmed`.
    - `action_create_vendor_bill` (`:594`): tạo `account.move` từ dòng đã chọn, gán `move_id`, chuyển sang `confirmed`.
    - `action_create_combined_vendor_bill` (`:667`): gộp nhiều hóa đơn đã duyệt.
    - `action_import` (`:776`): nút nhập từ bảng điều khiển e-invoice, áp dụng cùng quy tắc, và chuyển `confirmed` nếu đã có hóa đơn kế toán.
16. **Thông báo.** Mỗi lần đổi trạng thái yêu cầu, `_ocr_activity_update` (`models/purchase_order.py`) tạo hoặc đóng việc cần làm trên đơn mua: "hóa đơn chờ duyệt" hoặc "yêu cầu OCR lỗi".

Chú thích cho phần còn lại của mã nguồn:
- Phân quyền (`security/ir.model.access.csv`): người mua hàng đọc, sửa, tạo yêu cầu OCR và hóa đơn đầu vào; người quản lý mua hàng được thêm quyền xóa. Quy tắc đa công ty (`security/ir_rule.xml`) lọc theo công ty của đơn mua.
- Cơ chế chờ: `queue_job` tạo job trong kênh `root_ai` của `xb_ai_integration`.
- Phiếu nhập được gắn vào hóa đơn qua quan hệ nhiều-nhiều `vendor_inbound_bill_stock_picking_rel` (`models/stock_picking.py`).

---

## 4. Cấu hình cần có

| Thiết lập | Nơi đặt | Ghi chú |
|---|---|---|
| Khóa API OpenAI | `xb_chatgpt_integration.openapi_api_key` (tham số hệ thống) | Thiếu khóa thì không mở được chức năng. |
| Model ChatGPT | `xb_chatgpt_integration.chatgp_model` | Mặc định `gpt-4o` nếu không cấu hình. |
| Prompt hệ thống | Cài đặt, tham số `xb_purchase_vendor_bill_ocr.system_prompt` | Để trống thì dùng prompt mặc định trong mã nguồn. |
| MST nhà cung cấp | Hồ sơ nhà cung cấp | Thiếu MST thì hóa đơn có MST sẽ bị chặn. |
| Đơn vị tính | Danh mục đơn vị | Có từ điển đồng nghĩa cho tấn, cái, bộ, hộp, thùng, cuộn, mét, khối, kg, lít, chuyến, cây, giờ, ngày. |
| Phụ thuộc | `purchase_stock`, `l10n_vn_xb_einvoice_sync_base`, `xb_purchase`, `xb_chatgpt_integration`, `queue_job`, `xb_ai_integration`, `mail` | Thư viện Python: `fitz` (PyMuPDF), `openai`, `pydantic`, `httpx`. |

---

## 5. Quy tắc đã được xác nhận

Các điểm sau đã được người dùng xác nhận là đúng nghiệp vụ:

1. **So MST:** chỉ so 10 ký tự đầu của MST. Khớp thì tiếp tục, khác thì chặn.
2. **Ngưỡng khớp dòng:** 45 điểm là hợp lý.
3. **Trùng với hóa đơn e-invoice:** khi hóa đơn OCR trùng với hóa đơn đã đồng bộ từ nhà cung cấp hóa đơn điện tử, dùng bản đã đồng bộ và xóa bản OCR cũ nếu chưa duyệt.
4. **Thuế suất:** một hóa đơn chỉ có một mức thuế, nên thuế suất dòng suy ra từ tỷ lệ tiền thuế trên tổng tiền chưa thuế là đúng.

---

## 6. Phần chưa đọc và chưa kiểm chứng

- **Gộp với hóa đơn e-invoice:** hàm `_find_synced_einvoice` và `_merge_into_synced_einvoice` (`models/vendor_bill_ocr_request.py:444` và `:458`) chưa đọc thân hàm. Mô tả ở mục 3 bước 8 chỉ dựa trên cách hai hàm được gọi.
- **Điểm chấm khớp:** hàm `_score_po_line` và `_find_po_line_by_code` (`models/vendor_inbound_bill_line.py:228` và `:253`) chưa đọc. Chỉ biết ngưỡng 45 và thứ tự ưu tiên.
- **File test:** `tests/test_ocr_logic.py` chưa đọc.
- **Giao diện:** các view chi tiết (`views/*.xml`) chỉ đọc tên nút và nhãn. Chưa kiểm tra điều kiện hiển thị theo trạng thái.
- **Phụ thuộc ngoài:** `xb_chatgpt_integration` và `xb_ai_integration` không có trong thư mục này. Chưa xác minh được cách gọi API và kênh hàng đợi.
- **Tài liệu nghiệp vụ:** chưa đối chiếu với `scm/luong-nghiep-vu-scm.md` và `scm/quy-trinh-cung-ung-scm.md` trong project.

---

## 7. Phương pháp

- Đọc trực tiếp: manifest, wizard, schema, model yêu cầu OCR (xử lý chính, gọi AI, chia đoạn), model hóa đơn đầu vào (trạng thái, duyệt, khớp, tạo phiếu nhập, tạo hóa đơn, nhập), model dòng (tên hàm, ngưỡng), `tools/text_match.py`, `purchase_order.py`, `stock_picking.py`, `res_config_settings.py`, nút trong view, file phân quyền và quy tắc đa công ty.
- Suy luận: mô tả các bước "người dùng thấy gì" trong mục 2 dựa trên tên nút và trạng thái trong mã, chưa kiểm tra trên giao diện thật.
