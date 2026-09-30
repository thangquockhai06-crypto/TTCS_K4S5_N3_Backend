/**
 * AUTOPLEAD CRM - TICKET SCRUM-31
 * Soạn Báo Giá Từ Cơ Hội - JavaScript Xử Lý Real-time & Tính Toán Tức Thời
 * 
 * 1. AC1: Kế thừa sản phẩm, thêm/xóa/sửa dòng sản phẩm linh hoạt
 * 2. AC2: Nhập chiết khấu theo % hoặc VNĐ, tự động tính lại thành tiền tức thì
 * 3. AC3: Tính mức chiết khấu tổng, tự động kích hoạt cảnh báo khi chạm ngưỡng duyệt 10%
 * 4. AC4: Tự động điền mẫu hiệu lực báo giá, điều khoản thanh toán & giao hàng
 * 5. AC5: Hỗ trợ lưu nháp và sửa tiếp được
 */

const DISCOUNT_APPROVAL_THRESHOLD = 10.0; // Ngưỡng duyệt 10%
const DISCOUNT_WARNING_THRESHOLD = 8.0;   // Ngưỡng cảnh báo cận kề 8%
const DEFAULT_VAT_PERCENT = 8.0;          // VAT 8%

function formatVND(amount) {
    const val = Math.round(Number(amount) || 0);
    return val.toLocaleString('vi-VN') + ' đ';
}

document.addEventListener('DOMContentLoaded', function () {
    initLineItems();
    initPresets();
    recalculateAllTotals();
});

// =========================================================================
// TIÊU CHÍ 1 & 2 (AC1 & AC2): DÒNG SẢN PHẨM & TÍNH TOÁN CHIẾT KHẤU TỨC THỜI
// =========================================================================

function initLineItems() {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;

    // Gắn sự kiện lắng nghe trên container table (Event Delegation)
    tableBody.addEventListener('input', function (e) {
        if (e.target.matches('.quantity-input, .price-input, .discount-value-input')) {
            const row = e.target.closest('tr');
            if (row) {
                calculateRow(row);
                recalculateAllTotals();
            }
        }
    });

    tableBody.addEventListener('change', function (e) {
        if (e.target.matches('.discount-type-select')) {
            const row = e.target.closest('tr');
            if (row) {
                // Cập nhật placeholder gợi ý theo loại chiết khấu
                const valInput = row.querySelector('.discount-value-input');
                if (valInput) {
                    if (e.target.value === 'PERCENT') {
                        valInput.placeholder = '% (0 - 100)';
                        valInput.max = 100;
                    } else {
                        valInput.placeholder = 'Số tiền (VNĐ)';
                        valInput.removeAttribute('max');
                    }
                }
                calculateRow(row);
                recalculateAllTotals();
            }
        }
    });
}

/**
 * Tính toán tài chính cho một dòng sản phẩm (AC2)
 */
function calculateRow(row) {
    const qtyInput = row.querySelector('.quantity-input');
    const priceInput = row.querySelector('.price-input');
    const typeSelect = row.querySelector('.discount-type-select');
    const valInput = row.querySelector('.discount-value-input');

    const subtotalDisplay = row.querySelector('.row-subtotal-display');
    const discountAmountDisplay = row.querySelector('.row-discount-display');
    const totalDisplay = row.querySelector('.row-total-display');

    if (!qtyInput || !priceInput || !typeSelect || !valInput) return;

    const qty = Math.max(0, parseFloat(qtyInput.value) || 0);
    const unitPrice = Math.max(0, parseFloat(priceInput.value) || 0);
    const lineSubtotal = qty * unitPrice;

    const discountType = typeSelect.value;
    let discountVal = Math.max(0, parseFloat(valInput.value) || 0);
    let discountAmount = 0;

    if (discountType === 'PERCENT') {
        if (discountVal > 100) {
            discountVal = 100;
            valInput.value = 100;
        }
        discountAmount = lineSubtotal * (discountVal / 100.0);
    } else {
        // Chiết khấu theo số tiền cố định (VNĐ)
        if (discountVal > lineSubtotal) {
            discountVal = lineSubtotal; // Không giảm quá thành tiền gốc
        }
        discountAmount = discountVal;
    }

    const lineTotal = Math.max(0, lineSubtotal - discountAmount);

    // Cập nhật hiển thị lên DOM
    if (subtotalDisplay) subtotalDisplay.textContent = formatVND(lineSubtotal);
    if (discountAmountDisplay) discountAmountDisplay.textContent = formatVND(discountAmount);
    if (totalDisplay) totalDisplay.textContent = formatVND(lineTotal);

    // Lưu các giá trị tính được vào thuộc tính data của row để tính tổng
    row.dataset.subtotal = lineSubtotal;
    row.dataset.discountAmount = discountAmount;
    row.dataset.total = lineTotal;
}

/**
 * Thêm một dòng sản phẩm mới vào báo giá (AC1: Sửa lại được)
 */
function addNewRow() {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;

    const rowCount = tableBody.querySelectorAll('tr').length;
    const newIndex = rowCount + 1;

    const tr = document.createElement('tr');
    tr.dataset.subtotal = 0;
    tr.dataset.discountAmount = 0;
    tr.dataset.total = 0;

    tr.innerHTML = `
        <td style="text-align: center; color: #64748b; font-weight: 700;">${newIndex}</td>
        <td>
            <input type="hidden" name="item_id[]" value="">
            <input type="hidden" name="product_id[]" value="">
            <input type="hidden" name="product_code[]" value="PRD-CUSTOM">
            <input type="text" name="product_name[]" class="line-input" placeholder="Tên sản phẩm / dịch vụ..." required>
            <input type="text" name="description[]" class="line-input" style="font-size: 0.78rem; color: #64748b; margin-top: 4px;" placeholder="Ghi chú cấu hình / tính năng...">
        </td>
        <td style="width: 100px;">
            <input type="text" name="unit[]" class="line-input" value="Gói" style="text-align: center;">
        </td>
        <td style="width: 90px;">
            <input type="number" name="quantity[]" class="line-input quantity-input" value="1" min="1" step="1" style="text-align: right;" required>
        </td>
        <td style="width: 140px;">
            <input type="number" name="unit_price[]" class="line-input price-input" value="0" min="0" step="100000" style="text-align: right;" required>
            <div class="row-subtotal-display" style="font-size: 0.75rem; color: #64748b; text-align: right; margin-top: 2px;">0 đ</div>
        </td>
        <td style="width: 200px;">
            <div class="discount-group">
                <select name="discount_type[]" class="discount-type-select">
                    <option value="PERCENT" selected>%</option>
                    <option value="AMOUNT">VNĐ</option>
                </select>
                <input type="number" name="discount_value[]" class="line-input discount-value-input" value="0" min="0" step="any" placeholder="% (0 - 100)" style="text-align: right;">
            </div>
            <div class="row-discount-display" style="font-size: 0.75rem; color: #ef4444; text-align: right; margin-top: 2px;">Giảm: 0 đ</div>
        </td>
        <td style="width: 150px; text-align: right; font-weight: 700; color: #0f172a;">
            <span class="row-total-display">0 đ</span>
        </td>
        <td style="width: 50px; text-align: center;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="removeRow(this)" title="Xóa dòng sản phẩm này" style="color: #ef4444; padding: 4px 8px;">
                🗑️
            </button>
        </td>
    `;

    tableBody.appendChild(tr);
    calculateRow(tr);
    recalculateAllTotals();
    updateRowIndices();
}

/**
 * Chọn sản phẩm từ danh mục có sẵn và nạp vào bảng
 */
function addProductFromCatalog(product) {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;

    const rowCount = tableBody.querySelectorAll('tr').length;
    const newIndex = rowCount + 1;

    const tr = document.createElement('tr');
    tr.dataset.subtotal = product.price;
    tr.dataset.discountAmount = 0;
    tr.dataset.total = product.price;

    tr.innerHTML = `
        <td style="text-align: center; color: #64748b; font-weight: 700;">${newIndex}</td>
        <td>
            <input type="hidden" name="item_id[]" value="">
            <input type="hidden" name="product_id[]" value="${product.id}">
            <input type="hidden" name="product_code[]" value="${product.code}">
            <input type="text" name="product_name[]" class="line-input" value="${product.name}" required>
            <input type="text" name="description[]" class="line-input" style="font-size: 0.78rem; color: #64748b; margin-top: 4px;" value="${product.description || ''}">
        </td>
        <td style="width: 100px;">
            <input type="text" name="unit[]" class="line-input" value="${product.unit || 'Gói'}" style="text-align: center;">
        </td>
        <td style="width: 90px;">
            <input type="number" name="quantity[]" class="line-input quantity-input" value="1" min="1" step="1" style="text-align: right;" required>
        </td>
        <td style="width: 140px;">
            <input type="number" name="unit_price[]" class="line-input price-input" value="${product.price}" min="0" step="100000" style="text-align: right;" required>
            <div class="row-subtotal-display" style="font-size: 0.75rem; color: #64748b; text-align: right; margin-top: 2px;">${formatVND(product.price)}</div>
        </td>
        <td style="width: 200px;">
            <div class="discount-group">
                <select name="discount_type[]" class="discount-type-select">
                    <option value="PERCENT" selected>%</option>
                    <option value="AMOUNT">VNĐ</option>
                </select>
                <input type="number" name="discount_value[]" class="line-input discount-value-input" value="0" min="0" step="any" placeholder="% (0 - 100)" style="text-align: right;">
            </div>
            <div class="row-discount-display" style="font-size: 0.75rem; color: #ef4444; text-align: right; margin-top: 2px;">Giảm: 0 đ</div>
        </td>
        <td style="width: 150px; text-align: right; font-weight: 700; color: #0f172a;">
            <span class="row-total-display">${formatVND(product.price)}</span>
        </td>
        <td style="width: 50px; text-align: center;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="removeRow(this)" title="Xóa dòng sản phẩm này" style="color: #ef4444; padding: 4px 8px;">
                🗑️
            </button>
        </td>
    `;

    tableBody.appendChild(tr);
    calculateRow(tr);
    recalculateAllTotals();
    updateRowIndices();
}

/**
 * Xóa một dòng sản phẩm khỏi bảng (AC1)
 */
function removeRow(btn) {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;

    const rows = tableBody.querySelectorAll('tr');
    if (rows.length <= 1) {
        alert("Báo giá cần có ít nhất 01 dòng sản phẩm!");
        return;
    }

    const tr = btn.closest('tr');
    if (tr) {
        tr.remove();
        recalculateAllTotals();
        updateRowIndices();
    }
}

function updateRowIndices() {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;
    const rows = tableBody.querySelectorAll('tr');
    rows.forEach((row, idx) => {
        const firstCol = row.querySelector('td:first-child');
        if (firstCol) firstCol.textContent = idx + 1;
    });
}

// =========================================================================
// TIÊU CHÍ 3 (AC3): HIỂN THỊ MỨC CHIẾT KHẤU TỔNG & CẢNH BÁO CHẠM NGƯỠNG DUYỆT
// =========================================================================

function recalculateAllTotals() {
    const tableBody = document.getElementById('lineItemsBody');
    if (!tableBody) return;

    const rows = tableBody.querySelectorAll('tr');
    let subtotal = 0;
    let totalDiscount = 0;

    rows.forEach(row => {
        // Đảm bảo row đã được tính
        calculateRow(row);
        subtotal += parseFloat(row.dataset.subtotal) || 0;
        totalDiscount += parseFloat(row.dataset.discountAmount) || 0;
    });

    let overallDiscountPercent = 0;
    if (subtotal > 0) {
        overallDiscountPercent = Math.round((totalDiscount / subtotal) * 10000) / 100;
    }

    const amountAfterDiscount = Math.max(0, subtotal - totalDiscount);
    const vatAmount = Math.round(amountAfterDiscount * (DEFAULT_VAT_PERCENT / 100.0));
    const grandTotal = amountAfterDiscount + vatAmount;

    // Cập nhật DOM các chỉ số tổng hợp
    const subtotalElem = document.getElementById('summarySubtotal');
    const discountAmountElem = document.getElementById('summaryDiscountAmount');
    const discountPercentElem = document.getElementById('summaryDiscountPercent');
    const afterDiscountElem = document.getElementById('summaryAfterDiscount');
    const vatElem = document.getElementById('summaryVat');
    const grandTotalElem = document.getElementById('summaryGrandTotal');

    if (subtotalElem) subtotalElem.textContent = formatVND(subtotal);
    if (discountAmountElem) discountAmountElem.textContent = formatVND(totalDiscount);
    if (discountPercentElem) discountPercentElem.textContent = overallDiscountPercent.toFixed(1) + '%';
    if (afterDiscountElem) afterDiscountElem.textContent = formatVND(amountAfterDiscount);
    if (vatElem) vatElem.textContent = formatVND(vatAmount);
    if (grandTotalElem) grandTotalElem.textContent = formatVND(grandTotal);

    // XỬ LÝ CẢNH BÁO NGƯỠNG PHÊ DUYỆT (AC3)
    updateApprovalAlertBox(overallDiscountPercent);
}

function updateApprovalAlertBox(discountPercent) {
    const alertBox = document.getElementById('approvalAlertContainer');
    const submitBtn = document.getElementById('btnSubmitQuote');
    if (!alertBox) return;

    if (discountPercent >= DISCOUNT_APPROVAL_THRESHOLD) {
        // VƯỢT HOẶC CHẠM NGƯỠNG DUYỆT (>= 10.0%)
        alertBox.className = 'approval-alert-box alert-danger-urgent';
        alertBox.style.display = 'flex';
        alertBox.innerHTML = `
            <div style="font-size: 1.8rem; line-height: 1;">⚠️</div>
            <div>
                <div style="font-weight: 800; font-size: 1rem; color: #991b1b; margin-bottom: 4px;">
                    CẢNH BÁO: MỨC CHIẾT KHẤU TỔNG ĐẠT ${discountPercent.toFixed(1)}% (CHẠM/VƯỢT NGƯỠNG CHO PHÉP ${DISCOUNT_APPROVAL_THRESHOLD}%)
                </div>
                <div style="font-size: 0.88rem; line-height: 1.4;">
                    Theo chính sách kinh doanh công ty, Nhân viên kinh doanh chỉ có thẩm quyền chiết khấu tối đa <strong>${DISCOUNT_APPROVAL_THRESHOLD}%</strong>.<br>
                    Báo giá này <strong>BẮT BUỘC PHẢI ĐƯỢC TRƯỞNG NHÓM HOẶC GIÁM ĐỐC KINH DOANH PHÊ DUYỆT</strong> trước khi được phát hành chính thức tới khách hàng!
                </div>
            </div>
        `;
        if (submitBtn) {
            submitBtn.className = 'btn btn-warning btn-lg';
            submitBtn.innerHTML = `⚠️ Gửi Báo Giá Sang Chờ Duyệt (Chiết khấu ${discountPercent.toFixed(1)}% >= 10%)`;
        }
    } else if (discountPercent >= DISCOUNT_WARNING_THRESHOLD) {
        // CẬN KỀ NGƯỠNG DUYỆT (8.0% - 9.9%)
        alertBox.className = 'approval-alert-box alert-warning-soft';
        alertBox.style.display = 'flex';
        alertBox.innerHTML = `
            <div style="font-size: 1.6rem; line-height: 1;">⚡</div>
            <div>
                <div style="font-weight: 700; font-size: 0.95rem; color: #92400e; margin-bottom: 2px;">
                    LƯU Ý: Mức chiết khấu tổng đạt ${discountPercent.toFixed(1)}% (tiệm cận ngưỡng duyệt ${DISCOUNT_APPROVAL_THRESHOLD}%)
                </div>
                <div style="font-size: 0.85rem;">
                    Báo giá vẫn nằm trong hạn mức tự quyết của bạn (${discountPercent.toFixed(1)}% < ${DISCOUNT_APPROVAL_THRESHOLD}%). Nếu tăng thêm chiết khấu, hệ thống sẽ tự động chuyển sang luồng Trưởng nhóm duyệt.
                </div>
            </div>
        `;
        if (submitBtn) {
            submitBtn.className = 'btn btn-primary btn-lg';
            submitBtn.innerHTML = `🚀 Hoàn Tất & Gửi Báo Giá Ngay Buổi Chiều`;
        }
    } else {
        // AN TOÀN TRONG HẠN MỨC (< 8.0%)
        alertBox.className = 'approval-alert-box alert-success-soft';
        alertBox.style.display = 'flex';
        alertBox.innerHTML = `
            <div style="font-size: 1.4rem; line-height: 1;">✅</div>
            <div>
                <div style="font-weight: 700; font-size: 0.92rem; color: #065f46; margin-bottom: 2px;">
                    Chiết khấu tổng hợp lệ: ${discountPercent.toFixed(1)}% (Dưới ngưỡng phê duyệt ${DISCOUNT_APPROVAL_THRESHOLD}%)
                </div>
                <div style="font-size: 0.84rem;">
                    Báo giá đủ điều kiện gửi thẳng cho khách hàng ngay trong buổi chiều cùng ngày mà không cần chờ phê duyệt.
                </div>
            </div>
        `;
        if (submitBtn) {
            submitBtn.className = 'btn btn-primary btn-lg';
            submitBtn.innerHTML = `🚀 Hoàn Tất & Gửi Báo Giá Ngay Buổi Chiều`;
        }
    }
}

// =========================================================================
// TIÊU CHÍ 4 (AC4): ĐIỀU KHOẢN THANH TOÁN, GIAO HÀNG & HIỆU LỰC BÁO GIÁ
// =========================================================================

function initPresets() {
    // 1. Điều khoản thanh toán
    const paymentPresetSelect = document.getElementById('paymentPresetSelect');
    const paymentTextarea = document.getElementById('paymentTermsTextarea');
    if (paymentPresetSelect && paymentTextarea) {
        paymentPresetSelect.addEventListener('change', function () {
            if (this.value) {
                paymentTextarea.value = this.value;
            }
        });
    }

    // 2. Điều khoản giao hàng
    const deliveryPresetSelect = document.getElementById('deliveryPresetSelect');
    const deliveryTextarea = document.getElementById('deliveryTermsTextarea');
    if (deliveryPresetSelect && deliveryTextarea) {
        deliveryPresetSelect.addEventListener('change', function () {
            if (this.value) {
                deliveryTextarea.value = this.value;
            }
        });
    }

    // 3. Hiệu lực báo giá
    const validitySelect = document.getElementById('validityDaysSelect');
    const validUntilDisplay = document.getElementById('validUntilDisplay');
    if (validitySelect && validUntilDisplay) {
        validitySelect.addEventListener('change', function () {
            const days = parseInt(this.value) || 15;
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() + days);

            const dayStr = String(targetDate.getDate()).padStart(2, '0');
            const monthStr = String(targetDate.getMonth() + 1).padStart(2, '0');
            const yearStr = targetDate.getFullYear();

            validUntilDisplay.textContent = `${dayStr}/${monthStr}/${yearStr}`;
        });
    }
}
