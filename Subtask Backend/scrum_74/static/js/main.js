/**
 * JAVASCRIPT XỬ LÝ DRAWER MENU VÀ GIẢ LẬP MÀN HÌNH 360PX
 * Ticket: SCRUM-69 / SCRUM-74
 */

document.addEventListener("DOMContentLoaded", () => {
    const hamburgerBtn = document.getElementById("hamburger-btn");
    const closeDrawerBtn = document.getElementById("close-drawer-btn");
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("drawer-backdrop");
    const toggleSimBtn = document.getElementById("toggle-sim-btn");

    // =========================================================================
    // 1. MỞ VÀ ĐÓNG DRAWER MENU TRÊN MÀN HÌNH 360PX
    // =========================================================================
    function openDrawer() {
        if (sidebar && backdrop) {
            sidebar.classList.add("drawer-open");
            backdrop.classList.add("active");
            document.body.style.overflow = "hidden"; // Chống cuộn nền khi mở menu
        }
    }

    function closeDrawer() {
        if (sidebar && backdrop) {
            sidebar.classList.remove("drawer-open");
            backdrop.classList.remove("active");
            document.body.style.overflow = "";
        }
    }

    if (hamburgerBtn) {
        hamburgerBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            openDrawer();
        });
    }

    if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            closeDrawer();
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", () => {
            closeDrawer();
        });
    }

    // Đóng bằng phím Escape
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && sidebar && sidebar.classList.contains("drawer-open")) {
            closeDrawer();
        }
    });

    // Tự động đóng drawer khi chọn một mục menu trên màn hình di động
    const menuLinks = document.querySelectorAll(".menu-link");
    menuLinks.forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 992) {
                closeDrawer();
            }
        });
    });

    // =========================================================================
    // 2. TÍNH NĂNG GIẢ LẬP KHUNG ĐIỆN THOẠI 360PX
    // =========================================================================
    if (toggleSimBtn) {
        // Kiểm tra trạng thái đã lưu
        const savedSimState = localStorage.getItem("scrum74_simulator_active");
        if (savedSimState === "true") {
            enableSimulator();
        }

        toggleSimBtn.addEventListener("click", () => {
            if (document.body.classList.contains("simulator-mode")) {
                disableSimulator();
            } else {
                enableSimulator();
            }
        });
    }

    function enableSimulator() {
        document.body.classList.add("simulator-mode");
        if (toggleSimBtn) {
            toggleSimBtn.classList.add("active");
            toggleSimBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
                Trở lại màn hình lớn
            `;
        }
        localStorage.setItem("scrum74_simulator_active", "true");
        // Giả lập co về kích thước 360px
        const simFrame = document.querySelector(".simulator-viewport");
        if (simFrame) {
            simFrame.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    function disableSimulator() {
        document.body.classList.remove("simulator-mode");
        if (toggleSimBtn) {
            toggleSimBtn.classList.remove("active");
            toggleSimBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
                    <line x1="12" y1="18" x2="12.01" y2="18"></line>
                </svg>
                📱 Giả lập màn hình 360px
            `;
        }
        localStorage.setItem("scrum74_simulator_active", "false");
    }
});
