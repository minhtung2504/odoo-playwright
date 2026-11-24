# Test case: Quy trình cung ứng (Odoo CE 17 và module Xboss)

Nguồn: [quy-trinh-cung-ung-scm.md](/mnt/project-files/scm/quy-trinh-cung-ung-scm.md) và source trong `xboss-odoo/pms-scm-frm/` (xb_purchase, xb_stock, xb_purchase_requisition, material_purchase_requisitions).

## Cách đọc tài liệu này

- **Tiền điều kiện**: trạng thái dữ liệu cần có trước khi chạy case.
- **Các bước**: đi theo tên menu và nút trong mục 4 của quy trình. Tên nhãn có thể khác trên giao diện tiếng Việt.
- **[Kiểm tra]**: case phụ thuộc vào một điểm mà quy trình gốc đánh dấu chưa xác minh. Người chạy cần xác nhận nhãn và hành vi trên màn hình thật trước khi ghi kết quả.
- **[Xboss]**: case kiểm tra hành vi riêng của module Xboss trong source, khác hoặc bổ sung so với CE 17 chuẩn.
- **Trạng thái**: để trống. Ghi Đạt, Không đạt, hoặc Chặn (kèm lý do).
- Không chạy các case này trên môi trường production.

## Tổng hợp số case

| Khu vực | Số case |
|---|---|
| A. Thiết lập ban đầu (SET) | 11 |
| B. Tạo nhu cầu mua (NC) | 3 |
| C. Yêu cầu báo giá RFQ (RFQ) | 7 |
| D. Xác nhận và duyệt đơn (XN) | 6 |
| E. Nhận hàng (NH) | 9 |
| F. Hóa đơn nhà cung cấp (HD) | 8 |
| G. Thanh toán (TT) | 5 |
| H. Khóa đơn (KH) | 3 |
| I. Tồn kho và định giá (TK) | 5 |
| J. Lỗi thường gặp, phủ mục 7 (LOI) | 7 |
| K. Riêng Xboss: Blanket Order (XB-BO) | 6 |
| K. Riêng Xboss: Yêu cầu vật tư (XB-YC) | 9 |
| K. Riêng Xboss: Đơn mua và kho (XB-DM) | 4 |
| **Tổng** | **83** |

---

## A. Thiết lập ban đầu (SET)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| SET-01 | Tài khoản có quyền Inventory / Administrator | Inventory > Configuration > Warehouses > New. Nhập tên, mã kho, bấm Save. | Kho được tạo, có địa điểm nhận hàng và loại phiếu nhập mặc định. | |
| SET-02 | Có kho ở SET-01 | Mở kho, chọn Receipts = "1 step (receipts)". Lưu. Tạo đơn mua và nhận hàng. | Phiếu nhập đi thẳng vào kho, không có bước trung gian. | |
| SET-03 | Có kho ở SET-01 | Mở kho, chọn Receipts = "2 steps" hoặc "3 steps". Tạo đơn mua và nhận hàng. | Phiếu nhập có thêm bước kiểm trước khi cất hàng. [Kiểm tra] tên bước và nhãn trên giao diện. | |
| SET-04 | Quyền Inventory / Administrator | Inventory > Configuration > Settings. Bật Lots & Serial Numbers, Storage Locations, Multi-Step Routes. Lưu. | Các tùy chọn bật được, sản phẩm có ô Tracking và tuỳ chọn tuyến nhiều bước. | |
| SET-05 | Có sản phẩm loại hàng hóa | Mở sản phẩm, tab Purchase, thêm Vendor với đơn giá, Min. Quantity, Delivery Lead Time. Lưu. | Khi tạo RFQ chọn sản phẩm và nhà cung cấp này, đơn giá và thời gian giao được điền tự động. | |
| SET-06 | Sản phẩm ở SET-05 | Tab Purchase, mục Control Policy chọn "On ordered quantities". Sau đó chọn "On received quantities" ở một sản phẩm khác. | Hai tùy chọn lưu được. Hành vi tạo hóa đơn ở F-01 và F-02 khác nhau theo tùy chọn. [Kiểm tra] nhãn tiếng Việt. | |
| SET-07 | Sản phẩm ở SET-05 | Tab Inventory, mục Routes, chọn Buy. Thử chọn thêm Replenish on Order (MTO). | Chọn được cả Buy và MTO. Sản phẩm có Buy mới sinh đơn mua khi có nhu cầu. | |
| SET-08 | Quyền Accounting / Administrator | Inventory > Configuration > Product Categories > mở danh mục. Đặt Costing Method (Standard Price, Average Cost, FIFO) và Inventory Valuation = Automated. Kiểm tra tab Accounting có Stock Valuation Account, Stock Input/Output, Price Difference. | Các tài khoản được điền. Nếu thiếu tài khoản, hệ thống báo lỗi khi nhập kho. [Kiểm tra] tên trường Price Difference. | |
| SET-09 | Quyền Purchase / Administrator | Purchase > Configuration > Settings. Bật Purchase Agreements nếu dùng. Đặt Double Validation với ngưỡng tiền (ví dụ 50.000.000). Bật Lock Confirmed Orders. Lưu. | Các thiết lập được lưu. Trạng thái mặc định của Lock Confirmed Orders được ghi lại. [Kiểm tra] mặc định khi cài mới. | |
| SET-10 | Có sản phẩm và kho | Inventory > Operations > Replenishment > New. Nhập sản phẩm, Min = 10, Max = 50, Multiple Quantity = 5. Lưu. | Dòng quy tắc được tạo. Tồn dự báo dưới 10 sẽ có đề xuất đặt hàng. | |
| SET-11 | Có quy tắc ở SET-10 | Inventory > Operations > Replenishment, bấm Run Scheduler. | Đề xuất mua xuất hiện nếu tồn dự báo dưới Min. Không có lỗi trên màn hình. | |

## B. Tạo nhu cầu mua (NC)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| NC-01 | SET-05 đã làm | Purchase > Orders > Requests for Quotation > New. Chọn Vendor, thêm sản phẩm, bấm Save. | RFQ mới ở trạng thái RFQ (nháp). Có mã tự động dạng RFQxxxxx. | |
| NC-02 | SET-10 và SET-11 đã làm, tồn dưới Min | Inventory > Operations > Replenishment. Chọn dòng đề xuất, bấm Order. | Sinh RFQ với số lượng theo đề xuất. Dòng đề xuất biến mất khỏi danh sách đề xuất. | |
| NC-03 | Sản phẩm có route MTO và Buy (SET-07). Có khách hàng. | Sales > Orders > New, thêm sản phẩm MTO, bấm Confirm. Mở Purchase > Orders. | Có RFQ hoặc đơn mua mới, số lượng bằng đơn bán. Trường Origin trỏ về mã đơn bán. | |

## C. Yêu cầu báo giá RFQ (RFQ)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| RFQ-01 | Có nhà cung cấp có điều khoản thanh toán và tiền tệ | Purchase > Orders > RFQ > New. Chọn Vendor. | Điều khoản thanh toán và tiền tệ được điền theo nhà cung cấp. | |
| RFQ-02 | SET-05 đã làm | Thêm dòng sản phẩm đã có bảng giá nhà cung cấp, nhập số lượng. | Đơn giá lấy đúng từ bảng giá. Đổi số lượng đủ mốc giá thì đơn giá đổi theo. | |
| RFQ-03 | Có RFQ đang nháp | Điền Expected Arrival cho dòng sản phẩm. Lưu. | Ngày dự kiến được lưu và hiển thị ở dòng đơn. | |
| RFQ-04 | Có RFQ đang nháp và thỏa thuận khung (nếu dùng) | Điền Deadline. Chọn Agreement. | Hai trường được lưu. Agreement chỉ chọn được khi có thỏa thuận khung hợp lệ. | |
| RFQ-05 | RFQ-01 đến RFQ-03 xong | Bấm Send by Email, gửi thử tới địa chỉ nội bộ. | Trạng thái chuyển sang RFQ Sent. Email có đính kèm RFQ. | |
| RFQ-06 | RFQ đang nháp | Bấm Print RFQ. | Báo giá in ra đúng số lượng, đơn giá và tổng tiền. | |
| RFQ-07 | RFQ ở trạng thái RFQ hoặc RFQ Sent | Bấm Cancel. | Trạng thái thành Cancelled. Không sinh phiếu nhập. | |

## D. Xác nhận và duyệt đơn (XN)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| XN-01 | RFQ có tổng tiền dưới ngưỡng Double Validation | Mở RFQ, bấm Confirm Order. | Trạng thái thành Purchase Order. Sinh phiếu nhập ở trạng thái Waiting hoặc Ready. | |
| XN-02 | RFQ có tổng tiền vượt ngưỡng SET-09 | Mở RFQ, bấm Confirm Order. Đăng nhập tài khoản Trưởng mua hàng, mở đơn, bấm Approve Order. | Sau Confirm: To Approve. Sau Approve: Purchase Order. | |
| XN-03 | Đơn ở trạng thái To Approve | Đăng nhập tài khoản nhân viên mua hàng (không phải Trưởng). Tìm nút Approve Order. | Không thấy nút hoặc bị chặn quyền. [Kiểm tra] nhóm quyền thực tế. | |
| XN-04 | Đơn ở trạng thái To Approve, chưa duyệt | Mở Inventory > Operations > Receipts, tìm theo mã đơn. | Chưa có phiếu nhập cho đơn này. | |
| XN-05 | Đơn ở trạng thái Purchase Order và Lock Confirmed Orders bật | Mở đơn, thử sửa đơn giá hoặc số lượng ở dòng. | Trường không sửa được, hoặc hệ thống báo đơn đã khóa. Muốn sửa phải theo quy trình nội bộ. [Kiểm tra]. | |
| XN-06 | Đơn đã Confirm và đã có phiếu nhập chưa Done | Bấm Cancel trên đơn mua. | Quy định hủy đơn khi đã có phiếu nhập: [Kiểm tra] CE 17 cho phép hủy hay phải hủy phiếu trước. Ghi kết quả thực tế. | |

## E. Nhận hàng (NH)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| NH-01 | Đơn mua đã Confirm (XN-01) | Mở đơn, bấm nút Receipt. | Mở phiếu nhập liên kết với đơn. Trạng thái Waiting hoặc Ready. | |
| NH-02 | NH-01 xong, nhận đủ số lượng | Điền Quantity bằng số đặt cho mọi dòng. Bấm Validate. | Phiếu thành Done. Trên đơn, Receipt Status = Fully Received. [Kiểm tra] nhãn tiếng Việt. | |
| NH-03 | NH-01 xong, nhận thiếu | Điền Quantity thấp hơn số đặt. Bấm Validate. Trong hộp thoại Backorder, chọn Create Backorder. | Phiếu gốc Done theo số nhận. Phiếu backorder mới ở trạng thái Waiting hoặc Ready với phần còn lại. | |
| NH-04 | NH-01 xong, nhận thiếu | Như NH-03, chọn No Backorder. | Phiếu Done. Không sinh phiếu còn lại. Đơn hiển thị Receipt Status = Partially Received hoặc Fully Received theo quy trình. | |
| NH-05 | Sản phẩm có Lots, SET-04 đã bật | Mở phiếu nhập, điền Quantity, nhập số lô ở dòng chi tiết, Validate. | Phiếu Done. Tồn kho có lô tương ứng. | |
| NH-06 | Sản phẩm có Serial Number | Mở phiếu, nhập đủ serial cho từng đơn vị, Validate. | Phiếu Done. Mỗi serial có một bản ghi tồn kho. | |
| NH-07 | Phiếu đã Done, nhận thừa hoặc sai hàng | Mở phiếu Done, thử sửa số lượng. Bấm Return. | Không sửa được phiếu Done. Return tạo phiếu trả hàng, số lượng trả theo ý người dùng. | |
| NH-08 | Phiếu chưa Done | Để Quantity = 0 cho tất cả dòng, hoặc bỏ trống lô, rồi bấm Validate. | Hệ thống báo lỗi và không chuyển sang Done. | |
| NH-09 | Đơn có 2 dòng sản phẩm, chỉ nhận một dòng | Validate phiếu với một dòng đủ, dòng kia để 0. Chọn Backorder. | Phiếu backorder giữ dòng còn lại. Đơn ở trạng thái Partially Received. | |

## F. Hóa đơn nhà cung cấp (HD)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| HD-01 | Sản phẩm Control Policy = On ordered quantities (SET-06), đơn đã Confirm, chưa nhận | Mở đơn mua, bấm Create Bill. | Hóa đơn nháp được tạo với số lượng theo đơn đã đặt. | |
| HD-02 | Sản phẩm Control Policy = On received quantities, chưa nhận hàng | Mở đơn mua, bấm Create Bill. | Không tạo được hóa đơn cho dòng chưa nhận. Có thông báo hoặc không có dòng nào. | |
| HD-03 | Có đơn mua đã Confirm | Accounting > Vendors > Bills > New. Chọn nhà cung cấp, chọn đơn mua (hoặc thêm dòng). | Dòng hóa đơn lấy đúng sản phẩm và giá. Cách liên kết với đơn mua theo CE 17. [Kiểm tra]. | |
| HD-04 | Hóa đơn nháp | Điền Bill Reference (số hóa đơn của nhà cung cấp). Lưu. | Số tham chiếu được lưu và hiển thị trên hóa đơn. | |
| HD-05 | Hóa đơn nháp, đã kiểm tra ngày, thuế, tài khoản | Bấm Post. | Trạng thái Posted. Bút toán được ghi sổ. Trên đơn mua, Billing Status = Fully Billed. [Kiểm tra] nhãn. | |
| HD-06 | Đơn mua giá 100, hóa đơn nhà cung cấp giá 110 | Post hóa đơn. Kiểm tra bút toán. | Chênh lệch ghi vào tài khoản Price Difference (khi định giá tự động). [Kiểm tra] tài khoản và cách ghi nhận. | |
| HD-07 | Hóa đơn đã Posted có sai | Bấm Reverse (hoặc nút tương đương). Tạo lại hóa đơn đúng. | Có bút toán đảo. Hóa đơn mới đúng số tiền. Không sửa trực tiếp hóa đơn đã ghi sổ. | |
| HD-08 | Hóa đơn nháp | Bấm Cancel. | Trạng thái Cancelled. Không ghi sổ. | |

## G. Thanh toán (TT)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| TT-01 | Hóa đơn Posted, chưa trả | Mở hóa đơn, bấm Register Payment. Chọn sổ quỹ, số tiền bằng tổng hóa đơn, ngày. Xác nhận. | Trạng thái thanh toán = Paid. | |
| TT-02 | Hóa đơn Posted | Như TT-01, nhập số tiền nhỏ hơn tổng. | Trạng thái = Partially Paid. Còn số dư phải trả. | |
| TT-03 | Thanh toán đang chờ xử lý (phương thức có bước xác nhận) | Mở hóa đơn sau khi đăng ký thanh toán. | Trạng thái In Payment. [Kiểm tra] phương thức nào tạo trạng thái này. | |
| TT-04 | Có nhà cung cấp, chưa có hóa đơn | Tạo thanh toán ứng trước cho nhà cung cấp (Accounting > Vendors > Payments). | Bút toán thanh toán chưa đối ứng hóa đơn. Sau đó đối ứng khi có hóa đơn. [Kiểm tra]. | |
| TT-05 | Thanh toán đã ghi sổ | Mở thanh toán, bấm Reverse hoặc hủy theo quy trình. | Hóa đơn liên quan về trạng thái Not Paid hoặc Reversed. [Kiểm tra] nhãn tiếng Việt. | |

## H. Khóa đơn (KH)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| KH-01 | Đơn có Receipt Status = Fully Received, hóa đơn Paid | Mở đơn mua, bấm Lock. | Trạng thái Locked (done). | |
| KH-02 | Đơn đã Locked | Thử sửa đơn giá, số lượng, hoặc Delete. | Không sửa, không xóa được. Đơn chỉ để tra cứu. | |
| KH-03 | Đơn Confirm, chưa nhận hàng hoặc chưa thanh toán | Thử bấm Lock. | Hành vi theo CE 17. [Kiểm tra] có cho khóa khi chưa hoàn tất hay không. Ghi kết quả thực tế. | |

## I. Tồn kho và định giá (TK)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| TK-01 | NH-02 xong | Inventory > Reporting > Stock. Lọc theo sản phẩm và kho. | Số lượng tồn tăng đúng số đã nhận. | |
| TK-02 | Danh mục Automated, NH-02 xong | Inventory > Reporting > Valuation. Lọc theo sản phẩm. | Giá trị tồn = số lượng x đơn giá nhập. | |
| TK-03 | Danh mục AVCO, có 2 lần nhập giá khác nhau | Nhập lần 1 số lượng 10 giá 100. Nhập lần 2 số lượng 10 giá 120. Xem giá vốn. | Giá vốn bình quân là 110. | |
| TK-04 | Có tồn kho | Inventory > Operations > Physical Inventory. Nhập số đếm khác tồn, Apply. | Tồn kho điều chỉnh đúng số đếm. Có bút toán điều chỉnh nếu Automated. | |
| TK-05 | Hóa đơn đến sau phiếu nhập, giá khác (HD-06) | Kiểm tra giá vốn và giá trị tồn sau khi Post hóa đơn. | [Kiểm tra] cách CE 17 cập nhật giá vốn khi hóa đơn đến sau. Ghi kết quả thực tế. | |

## J. Lỗi thường gặp, phủ mục 7 của quy trình (LOI)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| LOI-01 | Sản phẩm không có route Buy, đơn đã Confirm | Mở phiếu nhập từ đơn mua đó. | Phiếu không sinh, hoặc đơn không có phiếu. Xử lý: thêm route Buy, Confirm lại. | |
| LOI-02 | Quy tắc đặt lại đã tắt hoặc Min/Max sai | Chạy Run Scheduler. | Đề xuất không xuất hiện. Xử lý: bật quy tắc, sửa Min/Max, chạy lại. | |
| LOI-03 | Đơn vượt ngưỡng, chưa duyệt | Bấm Confirm Order bằng tài khoản thường. | Đơn chuyển sang To Approve, không phải Purchase Order. Xử lý: Trưởng bấm Approve Order. | |
| LOI-04 | Đơn đã Confirm hoặc đã Locked | Thử Delete. | Không xóa được. Đơn nháp mới xóa được. Đơn đã xác nhận: Cancel nếu quy trình cho phép. | |
| LOI-05 | Phiếu nhập thiếu số lượng hoặc thiếu lô/serial | Bấm Validate. | Báo lỗi. Nhập đủ rồi Validate lại được. | |
| LOI-06 | Đơn đã Fully Billed, hoặc sản phẩm On received quantities chưa nhận | Bấm Create Bill. | Không tạo được hóa đơn. Xử lý: kiểm tra Billing Status và Control Policy. | |
| LOI-07 | Hóa đơn đã Posted có sai | Thử sửa trực tiếp. | Không sửa được. Xử lý: Reverse rồi tạo lại (HD-07). | |

---

## K. Riêng Xboss (XB) — đối chiếu với source

Các case này kiểm tra phần module Xboss thêm vào CE 17. Chúng không có trong quy trình chuẩn của doc gốc.

### K1. Blanket Order (xb_purchase_requisition)

Source: model `purchase.requisition` mở rộng bởi `xb_purchase_requisition`. Có trường `journal_id`, `exclusive` (kế thừa loại), `payment_ids`, `move_ids`, `project_id`, `contract_number`.

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| XB-BO-01 | Loại Blanket Order có exclusive = "Do not create RFQ" (no) | Tạo Blanket Order với loại này, thêm dòng, Confirm. | Không sinh RFQ. Loại này có cấu hình Create Bill riêng (trường `is_create_bill` của loại). Ghi lại giá trị thực tế trên loại. [Xboss] | |
| XB-BO-02 | Công ty chưa cấu hình Requisition Journal, Blanket Order không có Billing Journal | Bấm Create Bill trên Blanket Order. | Hệ thống báo: "Please select a journal for blanket orders or configure in the company settings." [Xboss] | |
| XB-BO-03 | Có Requisition Journal ở cấu hình công ty | Bấm Create Bill trên Blanket Order. | Hóa đơn nháp mở ra, journal lấy từ Blanket Order hoặc từ cấu hình công ty, dòng hóa đơn lấy từ dòng Blanket Order. | |
| XB-BO-04 | Blanket Order có loại Apply Price Same Product | Tạo RFQ, chọn Agreement là Blanket Order này. | Journal của RFQ lấy từ Blanket Order. Đơn giá cùng sản phẩm được gán theo giá Blanket Order. [Xboss] | |
| XB-BO-05 | Blanket Order có thanh toán ứng trước (Create Advance Payment) | Bấm Create Advance Payment, nhập số tiền, xác nhận. Mở Payments trên Blanket Order. | Thanh toán được tạo và liên kết với Blanket Order. Số dư còn lại (adv_amount_residual) đúng. | |
| XB-BO-06 | Công ty bật auto_paid_adv_payment_pr, hóa đơn khách hàng (out_invoice) | Post hóa đơn có Blanket Order liên quan. | Thanh toán ứng trước tự đối ứng vào hóa đơn. [Xboss] Lưu ý: cấu hình này áp dụng cho hóa đơn bán (out_invoice), cần kiểm tra luồng mua. | |

### K2. Yêu cầu vật tư (material_purchase_requisitions)

Source: model `material.purchase.requisition`. Đây là luồng riêng của Xboss, không có trong CE. Không liên quan đến `purchase.requisition` ở K1.

Các trạng thái theo source: New (draft), Waiting Department Approval (dept_confirm), Waiting IR Approval (ir_approve), Approved (approve), Picking / Purchase Created (stock), Received (receive), Cancelled (cancel), Rejected (reject).

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| XB-YC-01 | Có nhân viên, phòng ban, người dùng có nhóm Yêu cầu vật tư | Tạo Yêu cầu vật tư mới, thêm dòng, bấm Confirm. | Trạng thái: Waiting Department Approval. Ngày Confirm được ghi. [Xboss] | |
| XB-YC-02 | XB-YC-01 xong, tài khoản có nhóm Department | Bấm Department Approve. | Trạng thái: Waiting IR Approval. [Xboss] | |
| XB-YC-03 | XB-YC-02 xong, tài khoản có nhóm User | Bấm Approve. | Trạng thái: Approved. Nút Create Picking and PO xuất hiện. [Xboss] | |
| XB-YC-04 | Trạng thái Approved, có dòng loại Mua (purchase) với nhà cung cấp và dòng loại Nội bộ (internal) có đủ kho nguồn, loại phiếu, kho đích | Bấm Create Picking and PO. | Trạng thái: Picking / Purchase Created. Có phiếu xuất nội bộ và đơn mua theo từng nhà cung cấp. Đơn mua được tạo ở trạng thái nháp (RFQ). [Xboss] | |
| XB-YC-05 | Trạng thái Picking / Purchase Created | Bấm Show Picking hoặc Show PO (nút trên Yêu cầu). | Hiện đúng danh sách phiếu và đơn liên kết qua trường custom_requisition_id. [Xboss] | |
| XB-YC-06 | Trạng thái Picking / Purchase Created, đơn mua đã Confirm và nhập kho | Bấm Received. | Trạng thái: Received. Ngày nhận được ghi. [Xboss] | |
| XB-YC-07 | Trạng thái Waiting Department Approval, Waiting IR Approval hoặc Approved | Bấm Reject. | Trạng thái: Rejected. Người từ chối được ghi lại. Bấm Reset to Draft ở trạng thái Rejected, rồi sửa được. [Xboss] | |
| XB-YC-08 | Yêu cầu ở trạng thái Waiting Department Approval hoặc trạng thái khác draft | Thử xóa Yêu cầu. | Hệ thống chặn: chỉ xóa được khi trạng thái là New, Cancelled hoặc Rejected. [Xboss] | |
| XB-YC-09 | Có dòng loại Mua nhưng chưa chọn nhà cung cấp | Ở trạng thái Approved, bấm Create Picking and PO. | Báo lỗi: "Please enter atleast one vendor on Requisition Lines for Requisition Action Purchase". [Xboss] | |

Các điểm cần lưu ý khi chạy XB-YC:

- Source gán trạng thái `stock` trong vòng lặp tạo phiếu và đơn. Nếu lỗi giữa chừng, dữ liệu có thể dở dang. Nên thử trên bản sao dữ liệu.
- Trường nhãn trạng thái `Approved` và nhãn nút trong source là tiếng Anh. Giao diện tiếng Việt có thể khác. [Kiểm tra].
- Hai luồng Yêu cầu vật tư (material) và Blanket Order (purchase.requisition) khác nhau. Không đem chung case.

## K3. Đơn mua và kho (XB-DM)

| ID | Tiền điều kiện | Các bước | Kết quả mong đợi | Trạng thái |
|---|---|---|---|---|
| XB-DM-01 | Công ty bật is_required_journal, RFQ ở trạng thái nháp hoặc đã gửi | Mở RFQ, để trống Billing Journal, Save. | Trường Billing Journal bắt buộc. Khi đơn đã Confirm, trường không bắt buộc và chỉ đọc. [Xboss] | |
| XB-DM-02 | Có RFQ, Billing Journal đã chọn | Đổi journal sang sổ mua khác. Confirm đơn. Post hóa đơn từ đơn. | Hóa đơn tạo ra thuộc journal đã chọn trên đơn. [Xboss] | |
| XB-DM-03 | Sản phẩm có đơn vị đóng gói loại mua (packaging purchase) | Thêm sản phẩm vào RFQ. | Cờ hiển thị đóng gói bật, dòng có tuỳ chọn Use Product Packaging. [Xboss] | |
| XB-DM-04 | Kho có địa điểm đặt Block Valuation Entry on Return, có hàng trả về từ địa điểm này | Tạo phiếu trả hàng về địa điểm trên, Validate. | Không sinh bút toán giá trị cho dòng trả. Tồn kho số lượng vẫn cập nhật. [Xboss] | |

---

## Điểm cần người dùng xác nhận

1. Nhãn tiếng Việt thực tế của các nút: Receipt, Create Bill, Lock, Validate, Register Payment, Approve Order.
2. Cách CE 17 liên kết hóa đơn nhà cung cấp khi có nhiều phiếu nhập.
3. Quy định hủy đơn mua đã xác nhận khi phiếu nhập đã tạo (XN-06).
4. Tài khoản Price Difference và cách ghi nhận chênh lệch (HD-06, TK-05).
5. Mặc định của Lock Confirmed Orders và Double Validation trên môi trường thật (SET-09).
6. Nhóm quyền thực tế cho Approve Order (XN-03).
7. Bên Xboss: luồng Yêu cầu vật tư có đi qua RFQ hay không. Source tạo đơn mua ở trạng thái nháp. Cần xác nhận người dùng có Confirm đơn này trước khi nhận hàng không (XB-YC-04).

## Phạm vi và giới hạn

- Các case được viết từ tài liệu quy trình và đối chiếu với source các module Xboss (xb_purchase, xb_stock, xb_purchase_requisition, material_purchase_requisitions). Chưa chạy trên môi trường Odoo thật.
- Chưa kiểm tra source của module `purchase`, `stock`, `account` của CE 17. Các case thuộc CE chuẩn dựa vào tài liệu gốc.
- Không có case cho module Quality (chỉ bản Enterprise) và MRP chi tiết.
