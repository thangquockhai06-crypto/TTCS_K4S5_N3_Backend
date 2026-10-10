/**
 * AutoLead CRM - SCRUM-56 Main Interactive Scripts
 * Hỗ trợ các tương tác Modal Lưu Bộ Lọc & Ghi Nhận Cuộc Gọi Nhanh
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. MODAL LƯU BỘ LỌC (TIÊU CHÍ 3)
    const btnOpenSaveFilter = document.getElementById("btn-open-save-filter");
    const modalSaveFilter = document.getElementById("modal-save-filter");
    const btnCloseSaveFilter = document.getElementById("btn-close-save-filter");
    const btnCancelSaveFilter = document.getElementById("btn-cancel-save-filter");

    function openSaveFilterModal() {
        if (!modalSaveFilter) return;

        // Đồng bộ các tham số lọc hiện tại từ form chính vào form modal lưu
        const mainForm = document.getElementById("filter-form");
        if (mainForm) {
            const formData = new FormData(mainForm);
            for (let [key, val] of formData.entries()) {
                const hiddenInput = document.getElementById(`modal-criteria-${key}`);
                if (hiddenInput) {
                    hiddenInput.value = val;
                }
            }
        }

        modalSaveFilter.classList.add("open");
        const nameInput = document.getElementById("filter-name-input");
        if (nameInput) {
            nameInput.focus();
        }
    }

    function closeSaveFilterModal() {
        if (modalSaveFilter) {
            modalSaveFilter.classList.remove("open");
        }
    }

    if (btnOpenSaveFilter) {
        btnOpenSaveFilter.addEventListener("click", openSaveFilterModal);
    }
    if (btnCloseSaveFilter) {
        btnCloseSaveFilter.addEventListener("click", closeSaveFilterModal);
    }
    if (btnCancelSaveFilter) {
        btnCancelSaveFilter.addEventListener("click", closeSaveFilterModal);
    }

    // 2. MODAL GHI NHẬN CUỘC GỌI NHANH (GIẢI PHÓNG QUÁ HẠN SLA)
    const modalRecordCall = document.getElementById("modal-record-call");
    const btnCloseRecordCall = document.getElementById("btn-close-record-call");
    const btnCancelRecordCall = document.getElementById("btn-cancel-record-call");
    const callButtons = document.querySelectorAll(".btn-quick-call");

    callButtons.forEach((btn) => {
        btn.addEventListener("click", function () {
            const leadId = this.getAttribute("data-lead-id");
            const leadName = this.getAttribute("data-lead-name");
            const phone = this.getAttribute("data-phone");
            const isOverdue = this.getAttribute("data-overdue") === "true";

            const form = document.getElementById("form-record-call");
            if (form) {
                form.action = `/leads/${leadId}/call`;
            }

            const titleEl = document.getElementById("call-modal-lead-title");
            if (titleEl) {
                titleEl.textContent = `${leadName} (${leadId})`;
            }

            const phoneEl = document.getElementById("call-modal-phone");
            if (phoneEl) {
                phoneEl.textContent = phone;
                phoneEl.href = `tel:${phone}`;
            }

            const alertEl = document.getElementById("call-modal-sla-alert");
            if (alertEl) {
                alertEl.style.display = isOverdue ? "flex" : "none";
            }

            if (modalRecordCall) {
                modalRecordCall.classList.add("open");
            }
        });
    });

    function closeRecordCallModal() {
        if (modalRecordCall) {
            modalRecordCall.classList.remove("open");
        }
    }

    if (btnCloseRecordCall) {
        btnCloseRecordCall.addEventListener("click", closeRecordCallModal);
    }
    if (btnCancelRecordCall) {
        btnCancelRecordCall.addEventListener("click", closeRecordCallModal);
    }

    // 3. ĐÓNG MODAL KHI BẤM PHÍM ESC HOẶC CLICK NGOÀI
    window.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            closeSaveFilterModal();
            closeRecordCallModal();
        }
    });

    window.addEventListener("click", function (e) {
        if (e.target === modalSaveFilter) {
            closeSaveFilterModal();
        }
        if (e.target === modalRecordCall) {
            closeRecordCallModal();
        }
    });

    // 4. CHUYỂN ĐỔI PRESET KHOẢNG THỜI GIAN (CUSTOM DATE RANGE TOGGLE)
    const datePresetSelect = document.getElementById("date-preset-select");
    const customDateBox = document.getElementById("custom-date-box");

    if (datePresetSelect && customDateBox) {
        function toggleCustomDate() {
            if (datePresetSelect.value === "custom") {
                customDateBox.style.display = "flex";
            } else {
                customDateBox.style.display = "none";
            }
        }
        datePresetSelect.addEventListener("change", toggleCustomDate);
        toggleCustomDate();
    }
});
