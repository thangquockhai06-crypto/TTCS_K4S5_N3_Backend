/**
 * AUTOLEAD CRM - XỬ LÝ GIAO DIỆN & MODAL DUYỆT BÁO GIÁ (SCRUM-33)
 * Hỗ trợ Subtask FE: SCRUM-232 & Tương tác Backend BE: SCRUM-233
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Tự động đóng thông báo flash sau 6 giây
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.4s ease';
            setTimeout(function () {
                alert.remove();
            }, 400);
        }, 6000);
    });

    // 2. Chuyển đổi nhanh Persona qua Select Box
    const personaSelect = document.getElementById('persona-select');
    if (personaSelect) {
        personaSelect.addEventListener('change', function () {
            const userId = this.value;
            window.location.href = `/switch-persona/${userId}?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
        });
    }

    // 3. Xử lý Modal Phê Duyệt 3 Hành Động (Duyệt, Từ chối, Trả lại sửa) - AC3
    setupApprovalModal();

    // 4. Xử lý Form Tạo Báo Giá Động (Dynamic Quote Calculator)
    setupQuoteCalculator();
});

/**
 * Thiết lập Modal Phê Duyệt Báo Giá (AC3)
 */
function setupApprovalModal() {
    const modal = document.getElementById('approvalModal');
    if (!modal) return;

    const modalTitle = document.getElementById('modalTitle');
    const actionInput = document.getElementById('modalActionInput');
    const commentInput = document.getElementById('modalCommentInput');
    const commentLabel = document.getElementById('modalCommentLabel');
    const submitBtn = document.getElementById('modalSubmitBtn');
    const form = document.getElementById('approvalForm');

    // Nút mở modal Duyệt
    const btnApprove = document.getElementById('btnActionApprove');
    if (btnApprove) {
        btnApprove.addEventListener('click', function () {
            openModal({
                action: 'APPROVE',
                title: '✅ Xác Nhận Duyệt Báo Giá',
                label: 'Ý kiến phê duyệt (Tùy chọn):',
                required: false,
                btnClass: 'btn-success',
                btnText: '✅ Duyệt Ngay',
                placeholder: 'Nhập ý kiến hoặc lời dặn dò cho NVKD (không bắt buộc)...'
            });
        });
    }

    // Nút mở modal Từ chối
    const btnReject = document.getElementById('btnActionReject');
    if (btnReject) {
        btnReject.addEventListener('click', function () {
            openModal({
                action: 'REJECT',
                title: '❌ Xác Nhận Từ Chối Báo Giá',
                label: 'Lý do / Ý kiến từ chối (BẮT BUỘC):',
                required: true,
                btnClass: 'btn-danger',
                btnText: '❌ Xác Nhận Từ Chối',
                placeholder: 'Bắt buộc nhập lý do cụ thể vì sao từ chối báo giá này...'
            });
        });
    }

    // Nút mở modal Trả lại sửa
    const btnRequestChanges = document.getElementById('btnActionRequestChanges');
    if (btnRequestChanges) {
        btnRequestChanges.addEventListener('click', function () {
            openModal({
                action: 'REQUEST_CHANGES',
                title: '🔄 Xác Nhận Trả Lại Yêu Cầu Sửa',
                label: 'Ý kiến / Hướng dẫn chỉnh sửa (BẮT BUỘC):',
                required: true,
                btnClass: 'btn-warning',
                btnText: '🔄 Xác Nhận Trả Lại Sửa',
                placeholder: 'Bắt buộc nêu rõ các điểm cần sửa (ví dụ: hạ chiết khấu, đổi gói dịch vụ)...'
            });
        });
    }

    function openModal(config) {
        actionInput.value = config.action;
        modalTitle.textContent = config.title;
        commentLabel.innerHTML = config.label + (config.required ? ' <span class="required-star">*</span>' : '');
        commentInput.placeholder = config.placeholder;
        commentInput.value = '';

        submitBtn.className = 'btn ' + config.btnClass;
        submitBtn.textContent = config.btnText;

        modal.classList.add('active');
        setTimeout(() => commentInput.focus(), 150);
    }

    // Đóng Modal
    const closeBtns = modal.querySelectorAll('.modal-close, .btn-modal-cancel');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            modal.classList.remove('active');
        });
    });

    // Validation chặt chẽ trước khi Submit (AC3)
    if (form) {
        form.addEventListener('submit', function (e) {
            const action = actionInput.value;
            const comment = commentInput.value.trim();

            if ((action === 'REJECT' || action === 'REQUEST_CHANGES') && !comment) {
                e.preventDefault();
                alert(`⚠️ LỖI RÀNG BUỘC (AC3): Hành động '${action === 'REJECT' ? 'Từ chối' : 'Trả lại sửa'}' BẮT BUỘC phải nhập ý kiến/lý do cụ thể! Vui lòng không để trống.`);
                commentInput.focus();
                return false;
            }
        });
    }
}

/**
 * Tính toán báo giá thời gian thực trên form tạo mới
 */
function setupQuoteCalculator() {
    const tableBody = document.getElementById('quoteItemsBody');
    if (!tableBody) return;

    function recalculate() {
        let totalBefore = 0;
        let totalDiscount = 0;
        let totalFloor = 0;
        let belowFloorCount = 0;

        const rows = tableBody.querySelectorAll('tr.item-row');
        rows.forEach(row => {
            const qtyInput = row.querySelector('.item-qty');
            const priceInput = row.querySelector('.item-price');
            const discInput = row.querySelector('.item-disc');
            const floorPrice = parseFloat(row.dataset.floorPrice || 0);

            const qty = parseFloat(qtyInput ? qtyInput.value : 1) || 0;
            const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
            const discPct = parseFloat(discInput ? discInput.value : 0) || 0;

            const subtotalBefore = qty * price;
            const discAmount = subtotalBefore * (discPct / 100);
            const subtotalAfter = subtotalBefore - discAmount;
            const effectivePrice = qty > 0 ? (subtotalAfter / qty) : 0;
            const isBelowFloor = effectivePrice < floorPrice;

            totalBefore += subtotalBefore;
            totalDiscount += discAmount;
            totalFloor += (qty * floorPrice);
            if (isBelowFloor) belowFloorCount++;

            // Cập nhật DOM trên dòng
            const subtotalAfterEl = row.querySelector('.item-subtotal-after');
            if (subtotalAfterEl) {
                subtotalAfterEl.textContent = formatMoney(subtotalAfter);
            }

            const floorBadge = row.querySelector('.item-floor-badge');
            if (floorBadge) {
                if (isBelowFloor) {
                    floorBadge.innerHTML = `<span class="badge badge-floor-alert">🚨 Dưới sàn (${formatMoney(effectivePrice)} < ${formatMoney(floorPrice)})</span>`;
                } else {
                    floorBadge.innerHTML = `<span class="badge badge-slate">✓ Đạt sàn (${formatMoney(floorPrice)})</span>`;
                }
            }
        });

        const totalAfter = totalBefore - totalDiscount;
        const discountRate = totalBefore > 0 ? (totalDiscount / totalBefore * 100) : 0;
        const vatAmount = totalAfter * 0.08;
        const finalAmount = totalAfter + vatAmount;

        // Cập nhật bảng tổng kết
        document.getElementById('calcTotalBefore').textContent = formatMoney(totalBefore);
        document.getElementById('calcTotalDiscount').textContent = formatMoney(totalDiscount);
        document.getElementById('calcDiscountRate').textContent = discountRate.toFixed(1) + '%';
        document.getElementById('calcTotalAfter').textContent = formatMoney(totalAfter);
        document.getElementById('calcVatAmount').textContent = formatMoney(vatAmount);
        document.getElementById('calcFinalAmount').textContent = formatMoney(finalAmount);

        // Đánh giá thẩm quyền duyệt dự kiến
        const authorityCard = document.getElementById('calcAuthorityCard');
        if (authorityCard) {
            if (belowFloorCount > 0 || totalAfter < totalFloor) {
                authorityCard.className = 'card metric-card rose';
                authorityCard.innerHTML = `
                    <div class="metric-label">👑 THẨM QUYỀN DUYỆT DỰ KIẾN (BẮT BUỘC)</div>
                    <div class="metric-value" style="font-size: 1.3rem; color: #f87171;">GIÁM ĐỐC KINH DOANH</div>
                    <div class="metric-subtitle">🚨 CẢNH BÁO: Có ${belowFloorCount} sản phẩm bán dưới giá sàn! Bắt buộc Giám đốc duyệt để bảo vệ lợi nhuận.</div>
                `;
            } else if (discountRate > 20.0) {
                authorityCard.className = 'card metric-card rose';
                authorityCard.innerHTML = `
                    <div class="metric-label">👑 THẨM QUYỀN DUYỆT DỰ KIẾN (BẮT BUỘC)</div>
                    <div class="metric-value" style="font-size: 1.3rem; color: #f87171;">GIÁM ĐỐC KINH DOANH</div>
                    <div class="metric-subtitle">⚠️ Chiết khấu tổng ${discountRate.toFixed(1)}% vượt ngưỡng 2 (> 20.0%), thuộc thẩm quyền Giám đốc.</div>
                `;
            } else if (discountRate >= 10.0) {
                authorityCard.className = 'card metric-card amber';
                authorityCard.innerHTML = `
                    <div class="metric-label">👔 THẨM QUYỀN DUYỆT DỰ KIẾN</div>
                    <div class="metric-value" style="font-size: 1.3rem; color: #fbbf24;">TRƯỞNG NHÓM KINH DOANH</div>
                    <div class="metric-subtitle">📋 Chiết khấu ${discountRate.toFixed(1)}% nằm trong ngưỡng 1 (10% - 20%), cần Trưởng nhóm duyệt.</div>
                `;
            } else {
                authorityCard.className = 'card metric-card emerald';
                authorityCard.innerHTML = `
                    <div class="metric-label">⚡ THẨM QUYỀN DUYỆT DỰ KIẾN</div>
                    <div class="metric-value" style="font-size: 1.3rem; color: #34d399;">TỰ ĐỘNG THÔNG QUA</div>
                    <div class="metric-subtitle">✓ Chiết khấu ${discountRate.toFixed(1)}% dưới ngưỡng 1 (< 10%) và đảm bảo giá sàn -> Duyệt tự động ngay lập tức!</div>
                `;
            }
        }
    }

    tableBody.addEventListener('input', recalculate);
    tableBody.addEventListener('change', recalculate);

    // Xử lý thêm sản phẩm mới
    const addProductBtn = document.getElementById('btnAddProductRow');
    if (addProductBtn) {
        addProductBtn.addEventListener('click', function () {
            const productSelect = document.getElementById('productCatalogSelect');
            const selectedOption = productSelect.options[productSelect.selectedIndex];
            if (!selectedOption || !selectedOption.value) return;

            const prodId = selectedOption.value;
            const prodName = selectedOption.dataset.name;
            const listPrice = parseFloat(selectedOption.dataset.listPrice || 0);
            const floorPrice = parseFloat(selectedOption.dataset.floorPrice || 0);
            const unit = selectedOption.dataset.unit || 'Gói';

            const newRow = document.createElement('tr');
            newRow.className = 'item-row';
            newRow.dataset.floorPrice = floorPrice;
            newRow.innerHTML = `
                <td>
                    <strong>${prodName}</strong>
                    <input type="hidden" name="product_id[]" value="${prodId}">
                </td>
                <td>
                    <input type="number" class="form-control item-qty" name="quantity[]" value="1" min="1" style="width: 75px;">
                </td>
                <td>${unit}</td>
                <td>
                    <input type="number" class="form-control item-price" name="unit_price[]" value="${listPrice}" step="500000" style="width: 140px;">
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <input type="number" class="form-control item-disc" name="discount_percent[]" value="5" min="0" max="100" step="0.5" style="width: 75px;">
                        <span>%</span>
                    </div>
                </td>
                <td class="item-subtotal-after font-bold" style="color: #60a5fa;">${formatMoney(listPrice * 0.95)}</td>
                <td class="item-floor-badge">
                    <span class="badge badge-slate">✓ Đạt sàn (${formatMoney(floorPrice)})</span>
                </td>
                <td>
                    <button type="button" class="btn btn-outline btn-sm btn-remove-row" style="color: #f87171;">🗑️</button>
                </td>
            `;

            tableBody.appendChild(newRow);
            recalculate();
        });
    }

    // Xóa dòng
    tableBody.addEventListener('click', function (e) {
        if (e.target.closest('.btn-remove-row')) {
            const row = e.target.closest('.item-row');
            if (tableBody.querySelectorAll('.item-row').length > 1) {
                row.remove();
                recalculate();
            } else {
                alert('Báo giá phải có ít nhất một dòng sản phẩm!');
            }
        }
    });

    recalculate();
}

function formatMoney(amount) {
    try {
        return Math.round(amount).toLocaleString('vi-VN') + ' đ';
    } catch (e) {
        return amount + ' đ';
    }
}
