/**
 * AutoLead CRM - SCRUM-51 Interactive Logic
 * Features:
 * - Live SLA countdown timer
 * - Reject Lead Modal with strict reason requirement & quick preset chips
 * - Contact logging modal
 * - Reassign modal
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. LIVE SLA COUNTDOWN TIMERS
    initSlaCountdowns();

    // 2. MODAL CONTROLS
    initModals();

    // 3. PERSONA SWITCHER SELECT LISTENER
    const personaSelect = document.getElementById("persona-select");
    if (personaSelect) {
        personaSelect.addEventListener("change", function () {
            window.location.href = "/switch-user/" + this.value;
        });
    }

    // 4. AUTO REFRESH WORKER BADGE & NOTIFICATION BADGE
    setInterval(updateBackgroundWorkerStats, 5000);
});

// ==========================================
// ĐẾM NGƯỢC SLA THỜI GIAN THỰC (LIVE COUNTDOWN)
// ==========================================
function initSlaCountdowns() {
    const timerElements = document.querySelectorAll("[data-sla-deadline]");

    function updateTimers() {
        const now = new Date().getTime();

        timerElements.forEach((el) => {
            const deadlineIso = el.getAttribute("data-sla-deadline");
            const isContacted = el.getAttribute("data-contacted") === "true";
            const isFlagged = el.getAttribute("data-flagged") === "true";

            if (!deadlineIso || isContacted) {
                return; // Không cần đếm nếu không có hạn hoặc đã liên hệ xong
            }

            const deadline = new Date(deadlineIso).getTime();
            const distance = deadline - now;
            const totalSeconds = Math.floor(distance / 1000);

            if (totalSeconds > 0) {
                // Còn thời gian
                const minutes = Math.floor(totalSeconds / 60);
                const seconds = totalSeconds % 60;
                let formatted = "";

                if (minutes >= 60) {
                    const hours = Math.floor(minutes / 60);
                    const remMin = minutes % 60;
                    formatted = `${hours}h ${remMin}m`;
                } else {
                    formatted = `${minutes}m ${seconds < 10 ? "0" : ""}${seconds}s`;
                }

                el.textContent = `⏱️ Còn ${formatted}`;

                if (totalSeconds <= 30) {
                    el.className = "countdown-box countdown-yellow";
                } else {
                    el.className = "countdown-box countdown-green";
                }
            } else {
                // ĐÃ QUÁ HẠN SLA!
                const overdueSeconds = Math.abs(totalSeconds);
                const oMin = Math.floor(overdueSeconds / 60);
                const oSec = overdueSeconds % 60;
                el.textContent = `🚩 Quá hạn ${oMin > 0 ? oMin + "m " : ""}${oSec}s`;
                el.className = "countdown-box countdown-red";

                // Thêm viền đỏ báo động cho dòng nếu có
                const row = el.closest("tr");
                if (row && !row.classList.contains("row-flagged")) {
                    row.classList.add("row-flagged");
                }
            }
        });
    }

    updateTimers();
    setInterval(updateTimers, 1000);
}

// ==========================================
// ĐIỀU KHIỂN CÁC HỘP THOẠI MODAL
// ==========================================
function initModals() {
    // Đóng modal khi bấm nút x hoặc overlay
    document.querySelectorAll(".modal-close, .modal-cancel").forEach((btn) => {
        btn.addEventListener("click", function () {
            closeAllModals();
        });
    });

    document.querySelectorAll(".modal-overlay").forEach((overlay) => {
        overlay.addEventListener("click", function (e) {
            if (e.target === this) {
                closeAllModals();
            }
        });
    });

    // Mở Modal Từ Chối Lead
    document.querySelectorAll(".btn-open-reject-modal").forEach((btn) => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const leadId = this.getAttribute("data-lead-id");
            const leadName = this.getAttribute("data-lead-name") || leadId;

            const modal = document.getElementById("reject-modal");
            const form = document.getElementById("reject-form");
            const leadNameSpan = document.getElementById("reject-modal-lead-name");
            const reasonInput = document.getElementById("reject-reason-input");

            if (modal && form) {
                form.action = `/leads/${leadId}/reject`;
                if (leadNameSpan) leadNameSpan.textContent = `${leadName} (${leadId})`;
                if (reasonInput) reasonInput.value = "";

                // Reset chips
                document.querySelectorAll(".reason-chip").forEach((chip) => chip.classList.remove("selected"));

                modal.classList.add("open");
                if (reasonInput) reasonInput.focus();
            }
        });
    });

    // Xử lý chọn nhanh chip lý do từ chối
    document.querySelectorAll(".reason-chip").forEach((chip) => {
        chip.addEventListener("click", function () {
            document.querySelectorAll(".reason-chip").forEach((c) => c.classList.remove("selected"));
            this.classList.add("selected");
            const reasonText = this.getAttribute("data-reason");
            const reasonInput = document.getElementById("reject-reason-input");
            if (reasonInput) {
                reasonInput.value = reasonText;
                reasonInput.focus();
            }
        });
    });

    // Bắt buộc nhập lý do khi submit form từ chối (Tiêu chí 2)
    const rejectForm = document.getElementById("reject-form");
    if (rejectForm) {
        rejectForm.addEventListener("submit", function (e) {
            const reasonInput = document.getElementById("reject-reason-input");
            if (!reasonInput || !reasonInput.value.trim()) {
                e.preventDefault();
                alert("⚠️ BẮT BUỘC NHẬP LÝ DO! Theo quy định, nhân viên phải nêu rõ lý do trước khi từ chối lead.");
                if (reasonInput) reasonInput.focus();
            }
        });
    }

    // Mở Modal Ghi Nhận Liên Hệ
    document.querySelectorAll(".btn-open-contact-modal").forEach((btn) => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const leadId = this.getAttribute("data-lead-id");
            const leadName = this.getAttribute("data-lead-name") || leadId;

            const modal = document.getElementById("contact-modal");
            const form = document.getElementById("contact-form");
            const leadNameSpan = document.getElementById("contact-modal-lead-name");
            const notesInput = document.getElementById("contact-notes-input");

            if (modal && form) {
                form.action = `/leads/${leadId}/contact`;
                if (leadNameSpan) leadNameSpan.textContent = `${leadName} (${leadId})`;
                if (notesInput) notesInput.value = "";
                modal.classList.add("open");
                if (notesInput) notesInput.focus();
            }
        });
    });

    // Mở Modal Phân Bổ Lại Lead (Dành cho Trưởng nhóm)
    document.querySelectorAll(".btn-open-reassign-modal").forEach((btn) => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const leadId = this.getAttribute("data-lead-id");
            const leadName = this.getAttribute("data-lead-name") || leadId;

            const modal = document.getElementById("reassign-modal");
            const form = document.getElementById("reassign-form");
            const leadNameSpan = document.getElementById("reassign-modal-lead-name");

            if (modal && form) {
                form.action = `/leads/${leadId}/reassign`;
                if (leadNameSpan) leadNameSpan.textContent = `${leadName} (${leadId})`;
                modal.classList.add("open");
            }
        });
    });
}

function closeAllModals() {
    document.querySelectorAll(".modal-overlay").forEach((m) => m.classList.remove("open"));
}

// Cập nhật polling ngầm thông báo
function updateBackgroundWorkerStats() {
    fetch("/api/notifications/unread-count")
        .then((res) => res.json())
        .then((data) => {
            const badge = document.getElementById("unread-notif-badge");
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = "inline-block";
                } else {
                    badge.style.display = "none";
                }
            }
        })
        .catch(() => {});
}
