/**
 * MAIN INTERACTION SCRIPT FOR SCRUM-58
 * Quản lý người liên hệ và vai trò trong quyết định mua (B2B CRM)
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Tự động ẩn các thông báo Flash sau 6 giây
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-8px)";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // 2. Tương tác chọn Radio Cards Vai trò quyết định mua (Role Selector)
    const roleCards = document.querySelectorAll(".role-radio-card");
    roleCards.forEach(card => {
        card.addEventListener("click", () => {
            roleCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            const radio = card.querySelector("input[type='radio']");
            if (radio) radio.checked = true;
        });
    });

    // 3. Kiểm tra số điện thoại Việt Nam ngay khi nhập (Realtime Phone Feedback)
    const phoneInput = document.querySelector("input[type='tel']");
    if (phoneInput) {
        phoneInput.addEventListener("input", (e) => {
            const val = e.target.value.replace(/[\s.-]/g, "");
            const vnRegex = /^(?:\+?84|0)(3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}$/;
            
            if (val.length === 10 || (val.startsWith("+84") && val.length === 12)) {
                if (vnRegex.test(val)) {
                    phoneInput.style.borderColor = "#10b981";
                    phoneInput.style.backgroundColor = "#f0fdf4";
                } else {
                    phoneInput.style.borderColor = "#ef4444";
                    phoneInput.style.backgroundColor = "#fef2f2";
                }
            } else {
                phoneInput.style.borderColor = "";
                phoneInput.style.backgroundColor = "";
            }
        });
    }

    // 4. Smooth scrolling tới anchor (ví dụ #career-history)
    if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "start" });
            target.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.3)";
            setTimeout(() => target.style.boxShadow = "", 2000);
        }
    }
});
