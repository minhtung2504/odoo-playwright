# Quy trình cung ứng trên Odoo Community 17

Tài liệu mô tả quy trình cung ứng (mua hàng, nhập kho, tồn kho, hóa đơn nhà cung cấp, thanh toán) theo đúng module và menu của Odoo Community 17 (CE). Đây là quy trình chuẩn của Odoo, không phải quy trình riêng của Xboss.

**Nguồn và mức độ tin cậy.** Nội dung dựa trên kiến thức chung về Odoo CE 17 (các module `purchase`, `purchase_stock`, `purchase_requisition`, `stock`, `stock_account`, `account`). Chưa đối chiếu với source trong repo `xboss-odoo` và chưa thao tác trên môi trường thật. Các chi tiết cần người dùng kiểm tra được đánh dấu **[Kiểm tra]**. Khi chạy thử, ưu tiên xác nhận tên nút và tên trạng thái trên giao diện tiếng Việt, vì bản dịch có thể khác nhãn tiếng Anh.

## 0. Các khái niệm cần phân biệt

- **Yêu cầu mua (Purchase Agreement, CE)**: trong Odoo CE 17 là `purchase_requisition`, gồm hai loại: Blanket Order (thỏa thuận khung, mua nhiều đợt theo giá đã thống nhất) và Call for Tenders (đấu thầu, so sánh nhiều báo giá). Đây không phải là "Yêu cầu vật tư" của module `material_purchase_requisitions` trong repo Xboss. Muốn đối chiếu với các tài liệu Xboss, cần ghi rõ đang nói đến khái niệm nào.
- **Yêu cầu báo giá (RFQ)** và **Đơn mua (Purchase Order)** là hai trạng thái của cùng một bản ghi `purchase.order`.
- **Phiếu nhập kho (Receipt)** là một `stock.picking` có loại là nhập.
- **Quy tắc đặt hàng lại (Reordering Rule, orderpoint)** và **Mua theo đơn hàng (MTO)** là hai cách để hệ thống tự sinh nhu cầu mua.

## 1. Sơ đồ tổng quát

Nhu cầu (thủ công, quy tắc đặt lại, MTO từ đơn bán, hoặc thiếu nguyên liệu từ lệnh sản xuất)
→ Yêu cầu báo giá (RFQ) gửi nhà cung cấp
→ Xác nhận thành Đơn mua (Purchase Order)
→ Phiếu nhập kho (Receipt), kiểm số lượng và xác nhận (Validate)
→ Hóa đơn nhà cung cấp (Vendor Bill), ghi sổ (Post)
→ Thanh toán (Register Payment)
→ Khóa đơn mua (Lock)

## 2. Vai trò và nhóm quyền

Theo nhóm quyền chuẩn của CE 17 **[Kiểm tra]**:

| Vai trò | Nhóm quyền | Việc chính |
|---|---|---|
| Nhân viên mua hàng | Purchasing / User | Tạo RFQ, gửi nhà cung cấp, xác nhận đơn mua dưới ngưỡng |
| Trưởng mua hàng | Purchasing / Administrator | Duyệt đơn vượt ngưỡng (Double Validation), cấu hình nhà cung cấp |
| Thủ kho | Inventory / User | Nhận hàng, kiểm số lượng, xác nhận phiếu nhập |
| Quản trị kho | Inventory / Administrator | Cấu hình kho, tuyến (route), quy tắc đặt lại, kiểm kê |
| Kế toán | Accounting / Billing | Tạo, ghi sổ hóa đơn nhà cung cấp, thanh toán |

## 3. Thiết lập ban đầu (làm một lần)

Các bước này làm trước khi chạy nghiệp vụ. Thiếu một trong các thiết lập dưới đây thường là nguyên nhân chính khiến quy trình không chạy đúng.

### 3.1 Kho và tuyến (Inventory)
- Menu: Inventory / Configuration / Warehouses. Mỗi kho có địa điểm (location) nhận hàng, tuyến và loại phiếu.
- Tùy chọn **Receipts** của kho: "1 step (receipts)" là nhập thẳng vào kho. "2 steps" hay "3 steps" có thêm bước kiểm trước khi cất hàng. Nên chọn một lần và giữ nguyên.
- Trong Inventory / Configuration / Settings: bật Lots & Serial Numbers nếu hàng cần truy vết, bật Storage Locations nếu cần quản lý vị trí trong kho, bật Multi-Step Routes nếu dùng nhiều bước.

### 3.2 Sản phẩm (Purchase tab)
- Menu: Purchase / Products / Products, hoặc mở sản phẩm trong Inventory.
- Tab **Purchase**: thêm nhà cung cấp (Vendors) với giá, số lượng tối thiểu (Min. Quantity), thời gian giao (Delivery Lead Time). Đây là dữ liệu hệ thống dùng để chọn nhà cung cấp và tính ngày dự kiến khi tự sinh đơn.
- Tab **Purchase**, mục **Control Policy** (Bill Control): "On ordered quantities" cho phép lập hóa đơn theo số lượng đã đặt. "On received quantities" chỉ lập hóa đơn theo số lượng đã nhận. Đây là điểm quyết định khi tạo hóa đơn từ đơn mua. **[Kiểm tra]** nhãn tiếng Việt thực tế.
- Tab **Inventory**: Routes. Chọn **Buy** để sản phẩm được mua khi có nhu cầu. Chọn **Replenish on Order (MTO)** nếu sản phẩm được mua theo đơn bán. Có thể chọn cả hai.

### 3.3 Danh mục sản phẩm (định giá)
- Menu: Inventory / Configuration / Product Categories.
- **Costing Method**: Standard Price, Average Cost (AVCO) hoặc First In First Out (FIFO). Quyết định cách tính giá vốn khi nhập và xuất.
- **Inventory Valuation**: Manual hoặc Automated. Automated sẽ tự sinh bút toán tồn kho, cần cấu hình tài khoản.
- Tài khoản tồn kho (Stock Valuation Account), Stock Input/Output, Price Difference **[Kiểm tra]** trên tab Accounting của danh mục.

### 3.4 Cài đặt Mua hàng (Purchase Settings)
- Menu: Purchase / Configuration / Settings.
- **Purchase Agreements**: bật nếu dùng thỏa thuận khung hoặc đấu thầu.
- **Double Validation**: đặt số tiền tối thiểu. Đơn có giá trị vượt ngưỡng sẽ chuyển sang trạng thái To Approve và cần Trưởng mua hàng duyệt.
- **Lock Confirmed Orders**: khóa đơn mua đã xác nhận, không cho sửa trực tiếp. **[Kiểm tra]** có bật mặc định không.
- **Receipt Reminder**, **Purchase Lead Time**: nhắc nhận hàng và thời gian chờ mặc định.

### 3.5 Quy tắc đặt hàng lại (tùy chọn)
- Menu: Inventory / Operations / Replenishment.
- Thêm dòng cho sản phẩm với Min (mức tối thiểu), Max (mức tối đa) và Multiple Quantity (bội số đặt).
- Khi tồn dự báo xuống dưới Min, hệ thống tạo đề xuất mua. Đề xuất này sinh RFQ khi bấm Order hoặc khi bộ lập lịch chạy.

### 3.6 Bộ lập lịch (scheduler)
- Mặc định Odoo tự chạy lập lịch theo chu kỳ (thường mỗi ngày). Có thể chạy tay bằng nút Run Scheduler trong Replenishment.
- Nếu đề xuất mua không xuất hiện, kiểm tra quy tắc đặt lại (đã bật chưa, Min và Max đúng chưa), và kiểm tra cấu hình lập lịch **[Kiểm tra]**.

## 4. Quy trình chính từng bước

### 4.1 Tạo nhu cầu mua

Có ba nguồn nhu cầu:

1. **Thủ công**: người mua tự tạo RFQ (Purchase / Orders / Requests for Quotation, bấm New). Phù hợp với mua lẻ, không có định mức.
2. **Quy tắc đặt hàng lại**: hệ thống sinh đề xuất khi tồn xuống dưới mức tối thiểu (mục 3.5). Bấm Order trong Replenishment để sinh RFQ.
3. **Theo đơn hàng (MTO)**: khi xác nhận đơn bán có sản phẩm thuộc tuyến Replenish on Order (MTO), hệ thống tự sinh RFQ hoặc đơn mua tương ứng với đúng số lượng của đơn bán. Đơn mua này có liên kết với đơn bán gốc (Origin).
4. **Từ lệnh sản xuất (MRP, nếu dùng module Manufacturing)**: nguyên liệu thiếu trong lệnh sản xuất sinh nhu cầu mua theo tuyến Buy.

### 4.2 Lập RFQ (Yêu cầu báo giá)

1. Purchase / Orders / Requests for Quotation, bấm New.
2. Chọn **Vendor**. Hệ thống điền điều khoản thanh toán và tiền tệ theo nhà cung cấp.
3. Thêm dòng sản phẩm, số lượng, đơn giá (lấy từ bảng giá nhà cung cấp nếu có), ngày giao dự kiến (Expected Arrival).
4. Tùy chọn: **Deadline** (hạn trả lời) và **Agreement** (liên kết thỏa thuận khung).
5. Bấm **Send by Email** để gửi cho nhà cung cấp, hoặc **Print RFQ** để in. Trạng thái chuyển sang RFQ Sent.

Trạng thái RFQ: **RFQ** (nháp, draft) → **RFQ Sent** (đã gửi, sent). Có thể Cancel để hủy.

### 4.3 Xác nhận đơn mua

1. Khi nhà cung cấp đồng ý, bấm **Confirm Order**.
2. Nếu tổng tiền vượt ngưỡng Double Validation, trạng thái thành **To Approve**. Trưởng mua hàng bấm **Approve Order** để duyệt. Nếu chưa duyệt, đơn không sinh phiếu nhập.
3. Khi đơn được xác nhận, trạng thái thành **Purchase Order** (purchase). Hệ thống sinh phiếu nhập kho ở trạng thái Waiting hoặc Ready (xem mục 4.4).
4. Nếu hủy, bấm Cancel. Đơn đã xác nhận muốn hủy phải hủy phiếu nhập liên quan trước **[Kiểm tra]** quy định cụ thể của CE 17.
5. Khi hoàn tất, bấm **Lock** để khóa đơn (trạng thái Locked, done).

Trạng thái đơn mua: **Draft RFQ** → **RFQ Sent** → **To Approve** (nếu vượt ngưỡng) → **Purchase Order** → **Locked**. Đơn bị hủy là **Cancelled**.

Ghi chú: đơn đã xác nhận thường không cho sửa đơn giá hoặc số lượng trực tiếp nếu bật Lock Confirmed Orders. Muốn sửa phải hủy hoặc tạo điều chỉnh theo quy trình nội bộ **[Kiểm tra]**.

### 4.4 Nhận hàng (phiếu nhập kho)

1. Mở đơn mua, bấm nút **Receipt** (hoặc Inventory / Operations / Receipts).
2. Mở phiếu nhập. Với từng dòng, đối chiếu số lượng thực nhận và điền vào cột **Quantity** (số lượng hoàn thành).
3. Nếu hàng có lô hoặc serial, nhập số lô hoặc serial ở dòng chi tiết.
4. Bấm **Validate** để xác nhận nhập kho. Phiếu chuyển sang Done.
5. Nếu nhận thiếu, Odoo hiện hộp thoại **Backorder**: chọn **Create Backorder** để sinh phiếu nhập còn lại, hoặc **No Backorder** để đóng đơn theo số đã nhận.
6. Nếu nhận thừa hoặc không đúng hàng, không sửa phiếu đã Done. Dùng **Return** để tạo phiếu trả hàng, hoặc tạo điều chỉnh tồn kho.

Trạng thái phiếu nhập: **Draft** → **Waiting** (chờ hàng hoặc chờ phiếu khác) → **Ready** (sẵn sàng nhận) → **Done** (đã nhập kho). Có thể **Cancelled**.

Trên đơn mua có hai trạng thái theo dõi:
- **Receipt Status**: Nothing Received, Partially Received, Fully Received.
- **Billing Status**: Nothing to Bill, Waiting Bills, Fully Billed **[Kiểm tra]** nhãn tiếng Việt.

### 4.5 Hóa đơn nhà cung cấp

Có hai cách tạo:

1. **Từ đơn mua**: mở đơn, bấm **Create Bill**. Hệ thống dùng số lượng theo Control Policy của sản phẩm (đã đặt hoặc đã nhận).
2. **Thủ công**: Accounting / Vendors / Bills, bấm New. Chọn nhà cung cấp, nhập số hóa đơn của nhà cung cấp (Bill Reference), thêm dòng hoặc chọn đơn mua **[Kiểm tra]** cách liên kết trong CE 17.

Sau đó kiểm tra ngày, thuế, tài khoản của dòng, rồi bấm **Post** để ghi sổ.

Trạng thái hóa đơn: **Draft** → **Posted** (đã ghi sổ). Có thể **Cancelled**. Đã ghi sổ thì muốn sửa phải tạo bút toán đảo (Reverse) hoặc hủy theo quy trình kế toán.

Trạng thái thanh toán: **Not Paid**, **In Payment**, **Partially Paid**, **Paid**, **Reversed**.

Ghi chú về chênh lệch: nếu hóa đơn có giá khác đơn mua hoặc giá nhập kho, Odoo ghi chênh lệch vào tài khoản Price Difference (khi định giá tự động) **[Kiểm tra]**. Cần kế toán xác nhận tài khoản.

### 4.6 Thanh toán

1. Mở hóa đơn đã Post, bấm **Register Payment**.
2. Chọn sổ quỹ hoặc ngân hàng, số tiền, ngày thanh toán. Có thể thanh toán một phần.
3. Trạng thái hóa đơn tự cập nhật theo mục 4.5.

Thanh toán ứng trước cho nhà cung cấp cũng làm theo cách này, bằng bút toán thanh toán chưa đối ứng hóa đơn **[Kiểm tra]**.

### 4.7 Đóng chu trình

Khi hóa đơn đã thanh toán đủ và hàng đã nhận đủ, bấm **Lock** trên đơn mua. Sau đó đơn chỉ còn để tra cứu.

## 5. Tồn kho và định giá

- **Tồn kho hiện có**: Inventory / Reporting / Stock (theo sản phẩm, kho, lô).
- **Giá trị tồn**: Inventory / Reporting / Valuation (theo lớp định giá, cần bật Automated hoặc xem theo Stock Valuation Layer).
- **Kiểm kê**: Inventory / Operations / Physical Inventory. Nhập số đếm thực tế, Apply để điều chỉnh tồn kho.
- Giá vốn thay đổi theo phương pháp đã chọn (AVCO, FIFO hoặc Standard) khi nhận hàng và khi ghi hóa đơn có giá khác **[Kiểm tra]** cách Odoo CE 17 cập nhật giá vốn khi hóa đơn đến sau phiếu nhập.

## 6. Bảng trạng thái chứng từ

| Chứng từ | Trạng thái (nhãn tiếng Anh trong code) | Ý nghĩa |
|---|---|---|
| RFQ / Đơn mua | draft, sent, to approve, purchase, done, cancel | Nháp, đã gửi, chờ duyệt, đã xác nhận, đã khóa, hủy |
| Phiếu nhập/xuất | draft, waiting, confirmed, assigned, done, cancel | Nháp, chờ, chờ hàng, sẵn sàng, hoàn thành, hủy |
| Hóa đơn NCC | draft, posted, cancel | Nháp, đã ghi sổ, hủy |
| Thanh toán | not_paid, in_payment, partial, paid, reversed | Chưa trả, đang trả, trả một phần, đã trả, đảo |
| Đề xuất đặt hàng | (theo quy tắc đặt lại) | Đề xuất mua chưa thành đơn |

Các mã trên là mã kỹ thuật trong CE 17. Nhãn hiển thị có thể khác. **[Kiểm tra]** trên giao diện.

## 7. Lỗi thường gặp

| Tình huống | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Đơn mua không sinh phiếu nhập | Sản phẩm không có tuyến Buy, hoặc đơn chưa xác nhận | Thêm tuyến Buy, xác nhận đơn |
| Đề xuất đặt hàng không xuất hiện | Quy tắc đặt lại chưa bật, hoặc scheduler chưa chạy | Kiểm tra Min/Max, bấm Run Scheduler |
| Không thể xác nhận đơn | Đơn vượt ngưỡng Double Validation | Nhờ Trưởng mua hàng bấm Approve Order |
| Không xóa được đơn mua | Đơn đã xác nhận hoặc đã khóa | Hủy đơn (Cancel) nếu quy trình cho phép, hoặc xóa khi còn nháp |
| Không Validate được phiếu nhập | Thiếu số lượng hoặc lô/serial | Nhập số lượng, lô, serial đầy đủ |
| Hóa đơn không tạo được từ đơn mua | Đơn đã Fully Billed, hoặc Control Policy là đã nhận mà chưa nhận hàng | Kiểm tra Billing Status và Control Policy |
| Đã Post hóa đơn nhưng sai | Không sửa trực tiếp đã ghi sổ | Reverse hóa đơn rồi tạo lại |

## 8. Phân biệt với module Xboss (để BA đối chiếu)

| Khái niệm trong CE 17 | Tương ứng trong repo Xboss (theo tài liệu SCM hiện có) | Ghi chú |
|---|---|---|
| Purchase Agreement (Blanket Order) | `xb_purchase_requisition` | Cần xác nhận luồng khác nhau thế nào |
| Purchase Order (RFQ và đơn chính thức) | `purchase.order` mở rộng bởi `xb_purchase` | Cùng model, nhiều trường mở rộng |
| Receipt (phiếu nhập) | `stock.picking` mở rộng bởi `xb_stock` | Cùng model |
| Vendor Bill | `account.move` | Cùng model |
| Yêu cầu vật tư (Requisition) | `material_purchase_requisitions`, không có trong CE | Là luồng nghiệp vụ riêng, không phải chuẩn CE |
| Quality check khi nhận hàng | Module Quality, chỉ có ở bản Enterprise | Không có trong CE 17, không mô tả ở đây |

## 9. Điểm cần người dùng kiểm tra

1. Tên nhãn tiếng Việt của các nút và trạng thái trên giao diện CE 17 (Receipt, Create Bill, Lock, Validate, Register Payment).
2. Cách Odoo CE 17 liên kết hóa đơn NCC với đơn mua và phiếu nhập khi có nhiều phiếu.
3. Quy định hủy đơn mua đã xác nhận khi phiếu nhập đã tạo.
4. Tài khoản Price Difference và cách ghi nhận chênh lệch giá khi hóa đơn đến sau phiếu nhập.
5. Trạng thái và điều kiện kích hoạt bộ lập lịch đặt hàng lại trên môi trường thật.
6. Mức độ bật mặc định của Lock Confirmed Orders và Double Validation trong môi trường đang dùng.
7. Quy trình thực tế của Xboss có khác chuẩn CE 17 ở điểm nào (cần đối chiếu với repo `xboss-odoo`, không làm trong tài liệu này).

## 10. Phạm vi và giới hạn

- Có: quy trình chuẩn CE 17 cho mua hàng, nhận hàng, hóa đơn NCC, thanh toán, tồn kho và định giá cơ bản, quy tắc đặt hàng lại và MTO.
- Chưa có: module Quality (chỉ bản Enterprise), sản xuất chi tiết (MRP), dropshipping, nhập khẩu và chi phí nhập khẩu (landed cost), đa công ty.
- Chưa đối chiếu: source của repo Xboss, cấu hình thật của công ty, giao diện tiếng Việt.
