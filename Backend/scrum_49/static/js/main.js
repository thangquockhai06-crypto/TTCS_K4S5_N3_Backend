/**
 * JavaScript cho Hệ Thống Phân Bổ Lead Tự Động - SCRUM-30 / SCRUM-49
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Quản lý Modal
    const openModalBtns = document.querySelectorAll("[data-modal-target]");
    const closeModalBtns = document.querySelectorAll("[data-modal-close]");
    const overlays = document.querySelectorAll(".modal-overlay");

    openModalBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-modal-target");
            const modal = document.getElementById(targetId);
            if (modal) {
                modal.classList.add("active");
            }
        });
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const modal = btn.closest(".modal-overlay");
            if (modal) {
                modal.classList.remove("active");
            }
        });
    });

    overlays.forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.classList.remove("active");
            }
        });
    });

    // 2. Chuyển đổi phương thức phân bổ trong Form Quy tắc (Round-Robin vs Direct)
    const assignmentTypeSelects = document.querySelectorAll(".assignment-type-select");
    assignmentTypeSelects.forEach(select => {
        const form = select.closest("form");
        const teamGroup = form.querySelector(".group-target-team");
        const userGroup = form.querySelector(".group-target-user");

        const updateVisibility = () => {
            if (select.value === "ROUND_ROBIN") {
                if (teamGroup) teamGroup.style.display = "block";
                if (userGroup) userGroup.style.display = "none";
            } else {
                if (teamGroup) teamGroup.style.display = "none";
                if (userGroup) userGroup.style.display = "block";
            }
        };

        select.addEventListener("change", updateVisibility);
        updateVisibility();
    });

    // 3. Tự động đóng thông báo flash sau 6 giây
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // 4. Polling nhẹ nhàng cập nhật trạng thái Worker và KPI ngầm
    const liveWorkerBadge = document.getElementById("live-worker-badge");
    if (liveWorkerBadge) {
        setInterval(async () => {
            try {
                const res = await fetch("/api/status");
                if (res.ok) {
                    const data = await res.json();
                    if (data.worker && data.worker.is_running && !data.worker.is_paused) {
                        liveWorkerBadge.innerHTML = '<span class="pulse-dot"></span> Luồng nền đang chạy';
                    } else if (data.worker && data.worker.is_paused) {
                        liveWorkerBadge.innerHTML = '⏸️ Luồng nền tạm dừng';
                    }
                }
            } catch (err) {
                // Im lặng nếu không fetch được
            }
        }, 5000);
    }
});

function openManualAssignModal(leadId, leadCode, leadName, reason) {
    const modal = document.getElementById("manual-assign-modal");
    if (!modal) return;
    
    const form = modal.querySelector("form");
    if (form) {
        form.action = `/manual-queue/${leadId}/assign`;
    }
    
    const codeEl = modal.querySelector("#assign-lead-code");
    const nameEl = modal.querySelector("#assign-lead-name");
    const reasonEl = modal.querySelector("#assign-lead-reason");
    
    if (codeEl) codeEl.textContent = leadCode;
    if (nameEl) nameEl.textContent = leadName;
    if (reasonEl) reasonEl.textContent = reason || "Không khớp bất kỳ quy tắc nào trong hệ thống";
    
    modal.classList.add("active");
}
