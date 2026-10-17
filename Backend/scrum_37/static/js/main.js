/**
 * AUTOLEAD CRM - Xử lý tương tác Frontend (SCRUM-35 / SCRUM-37)
 * Subtask: SCRUM-234 (FE)
 * Hỗ trợ tính toán live chiết khấu, đối chiếu Side-by-side và Kích hoạt hiệu lực
 */

document.addEventListener('DOMContentLoaded', function () {
    initLineItemCalculations();
    initCompareSelectors();
    initSimulator();
});

/**
 * 1. Tự động tính toán tổng tiền, chiết khấu và thuế VAT trong Form Báo Giá
 */
function initLineItemCalculations() {
    const itemsTable = document.getElementById('items-tbody');
    if (!itemsTable) return;

    // Lắng nghe thay đổi trên các input số lượng, đơn giá, chiết khấu
    itemsTable.addEventListener('input', function (e) {
        if (e.target.matches('.calc-trigger')) {
            const row = e.target.closest('tr');
            recalculateRow(row);
            recalculateGrandTotals();
        }
    });

    // Thêm dòng sản phẩm mới
    const addRowBtn = document.getElementById('add-item-btn');
    if (addRowBtn) {
        addRowBtn.addEventListener('click', function () {
            addNewRow();
        });
    }

    // Xóa dòng sản phẩm
    itemsTable.addEventListener('click', function (e) {
        if (e.target.closest('.delete-row-btn')) {
            const row = e.target.closest('tr');
            const totalRows = itemsTable.querySelectorAll('tr').length;
            if (totalRows <= 1) {
                alert('Báo giá phải có ít nhất 1 dòng sản phẩm!');
                return;
            }
            row.remove();
            recalculateGrandTotals();
        }
    });

    // Tính toán ban đầu
    recalculateGrandTotals();
}

function recalculateRow(row) {
    if (!row) return;
    const qtyInput = row.querySelector('.item-qty');
    const priceInput = row.querySelector('.item-price');
    const discInput = row.querySelector('.item-disc');
    const amountSpan = row.querySelector('.item-amount-display');

    const qty = parseFloat(qtyInput ? qtyInput.value : 0) || 0;
    const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
    const discPct = parseFloat(discInput ? discInput.value : 0) || 0;

    const subtotal = qty * price;
    const discountAmt = subtotal * (discPct / 100.0);
    const finalAmount = Math.max(0, subtotal - discountAmt);

    if (amountSpan) {
        amountSpan.textContent = formatCurrencyVND(finalAmount);
    }
}

function recalculateGrandTotals() {
    const rows = document.querySelectorAll('#items-tbody tr');
    let subtotal = 0;
    let totalDiscount = 0;

    rows.forEach(row => {
        const qty = parseFloat(row.querySelector('.item-qty')?.value || 0) || 0;
        const price = parseFloat(row.querySelector('.item-price')?.value || 0) || 0;
        const discPct = parseFloat(row.querySelector('.item-disc')?.value || 0) || 0;

        const lineSubtotal = qty * price;
        const lineDiscount = lineSubtotal * (discPct / 100.0);

        subtotal += lineSubtotal;
        totalDiscount += lineDiscount;
    });

    const subtotalAfterDisc = Math.max(0, subtotal - totalDiscount);
    const vatInput = document.getElementById('vat-percent-input');
    const vatPercent = parseFloat(vatInput ? vatInput.value : 10) || 10;
    const vatAmount = subtotalAfterDisc * (vatPercent / 100.0);
    const grandTotal = subtotalAfterDisc + vatAmount;

    // Cập nhật lên UI
    const subtotalEl = document.getElementById('display-subtotal');
    const discountEl = document.getElementById('display-discount');
    const vatEl = document.getElementById('display-vat');
    const grandEl = document.getElementById('display-grand-total');

    if (subtotalEl) subtotalEl.textContent = formatCurrencyVND(subtotal);
    if (discountEl) discountEl.textContent = formatCurrencyVND(totalDiscount);
    if (vatEl) vatEl.textContent = formatCurrencyVND(vatAmount);
    if (grandEl) grandEl.textContent = formatCurrencyVND(grandTotal);
}

function addNewRow() {
    const tbody = document.getElementById('items-tbody');
    if (!tbody) return;

    const rowCount = tbody.querySelectorAll('tr').length + 1;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td class="text-center font-bold text-muted">${rowCount}</td>
        <td>
            <input type="text" name="product_name[]" class="form-control" placeholder="Tên sản phẩm / dịch vụ..." required>
            <input type="hidden" name="product_id[]" value="PROD-CUSTOM-${Date.now()}">
        </td>
        <td>
            <input type="text" name="unit[]" class="form-control" value="Gói" style="width: 80px;">
        </td>
        <td>
            <input type="number" name="quantity[]" class="form-control item-qty calc-trigger" value="1" min="1" step="1" style="width: 80px;">
        </td>
        <td>
            <input type="number" name="unit_price[]" class="form-control item-price calc-trigger" value="10000000" min="0" step="100000">
        </td>
        <td>
            <div style="display: flex; align-items: center; gap: 4px;">
                <input type="number" name="discount_percent[]" class="form-control item-disc calc-trigger" value="0" min="0" max="100" step="0.5" style="width: 70px;">
                <span>%</span>
            </div>
        </td>
        <td class="text-right font-bold">
            <span class="item-amount-display">10.000.000 đ</span>
        </td>
        <td>
            <input type="text" name="item_notes[]" class="form-control" placeholder="Ghi chú dòng...">
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-outline btn-sm delete-row-btn" style="color: #ef4444;" title="Xóa dòng">
                🗑️
            </button>
        </td>
    `;
    tbody.appendChild(tr);
    recalculateRow(tr);
    recalculateGrandTotals();
}

/**
 * 2. Xử lý đổi phiên bản so sánh Side-by-side
 */
function initCompareSelectors() {
    const selectV1 = document.getElementById('select-ver-1');
    const selectV2 = document.getElementById('select-ver-2');
    const compareBtn = document.getElementById('btn-apply-compare');

    if (compareBtn && selectV1 && selectV2) {
        compareBtn.addEventListener('click', function () {
            const v1 = selectV1.value;
            const v2 = selectV2.value;
            if (v1 === v2) {
                alert('Vui lòng chọn 2 phiên bản khác nhau để so sánh sự khác biệt!');
                return;
            }
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('v1', v1);
            currentUrl.searchParams.set('v2', v2);
            window.location.href = currentUrl.toString();
        });
    }

    const swapBtn = document.getElementById('btn-swap-versions');
    if (swapBtn && selectV1 && selectV2) {
        swapBtn.addEventListener('click', function () {
            const temp = selectV1.value;
            selectV1.value = selectV2.value;
            selectV2.value = temp;
        });
    }
}

/**
 * 3. Kích hoạt phiên bản hiệu lực DUY NHẤT qua AJAX (Tiêu chí 3)
 */
function setEffectiveVersion(versionId, versionTag, quoteCode) {
    if (!confirm(`Bạn có chắc chắn muốn kích hoạt phiên bản ${versionTag} thành PHIÊN BẢN HIỆU LỰC DUY NHẤT cho báo giá ${quoteCode}?\n\nMọi phiên bản khác sẽ tự động chuyển sang trạng thái hết hiệu lực.`)) {
        return;
    }

    fetch(`/api/quotes/${versionId}/set-effective`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ actor: 'Trần Văn Nam (NVKD)' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể kích hoạt phiên bản'));
        }
    })
    .catch(err => {
        alert('Lỗi kết nối máy chủ: ' + err);
    });
}

/**
 * 4. Gửi báo giá cho khách hàng qua AJAX
 */
function sendQuoteToCustomer(versionId, versionTag, quoteCode) {
    if (!confirm(`Xác nhận gửi báo giá phiên bản ${versionTag} cho khách hàng?\n\nLƯU Ý (Tiêu chí 1 & 3):\n1. Phiên bản này sẽ được đóng băng bất biến.\n2. Phiên bản này trở thành ĐANG HIỆU LỰC DUY NHẤT.\n3. Nếu cần chỉnh sửa sau này, hệ thống sẽ tự động tạo phiên bản mới.`)) {
        return;
    }

    fetch(`/api/quotes/${versionId}/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ actor: 'Trần Văn Nam (NVKD)' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể gửi báo giá'));
        }
    })
    .catch(err => {
        alert('Lỗi kết nối máy chủ: ' + err);
    });
}

/**
 * 5. Bộ mô phỏng kiểm thử tự động 3 Acceptance Criteria
 */
function initSimulator() {
    const runBtn = document.getElementById('btn-run-simulation');
    if (!runBtn) return;

    runBtn.addEventListener('click', function () {
        runBtn.disabled = true;
        runBtn.innerHTML = '⏳ Đang thực thi kịch bản kiểm thử...';

        const resultContainer = document.getElementById('simulation-results');
        if (resultContainer) {
            resultContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #2563eb;">🚀 Đang khởi tạo báo giá thử nghiệm và kiểm tra 3 Tiêu chí chấp nhận...</div>';
        }

        fetch('/api/simulator/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
            runBtn.disabled = false;
            runBtn.innerHTML = '▶️ Chạy Lại Bộ Kiểm Thử (1-Click Run)';

            if (data.success && resultContainer) {
                let html = '';
                data.results.forEach((r, idx) => {
                    const statusClass = r.passed ? 'passed' : 'failed';
                    const icon = r.passed ? '✅ ĐẠT' : '❌ THẤT BẠI';
                    html += `
                        <div class="simulator-step ${statusClass}" style="margin-bottom: 16px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <h4 style="font-weight: 700; color: ${r.passed ? '#065f46' : '#991b1b'};">
                                    Mục ${idx + 1}: ${r.criteria}
                                </h4>
                                <span class="badge ${r.passed ? 'badge-accepted' : 'badge-rejected'}" style="font-size: 13px;">${icon}</span>
                            </div>
                            <p style="color: #334155; font-size: 13.5px; line-height: 1.5;">${r.details}</p>
                        </div>
                    `;
                });

                if (data.all_passed) {
                    html = `
                        <div class="alert alert-success" style="margin-bottom: 20px; font-weight: 700; font-size: 15px;">
                            🎉 TẤT CẢ 3 TIÊU CHÍ CHẤP NHẬN ĐỀ BÀI ĐỀU ĐẠT 100%! HỆ THỐNG HOẠT ĐỘNG HOÀN HẢO.
                        </div>
                    ` + html;
                }

                resultContainer.innerHTML = html;
            } else {
                if (resultContainer) {
                    resultContainer.innerHTML = `<div class="alert alert-danger">Lỗi kiểm thử: ${data.error}</div>`;
                }
            }
        })
        .catch(err => {
            runBtn.disabled = false;
            runBtn.innerHTML = '▶️ Chạy Lại Bộ Kiểm Thử';
            if (resultContainer) {
                resultContainer.innerHTML = `<div class="alert alert-danger">Lỗi kết nối máy chủ: ${err}</div>`;
            }
        });
    });
}

/**
 * Định dạng tiền VND đẹp
 */
function formatCurrencyVND(amount) {
    try {
        return new Intl.NumberFormat('vi-VN').format(Math.round(amount)) + ' đ';
    } catch (e) {
        return amount + ' đ';
    }
}
