/**
 * AutoLead CRM - Ticket SCRUM-99
 * Client-Side JavaScript
 */

document.addEventListener("DOMContentLoaded", () => {
    // Tự động ẩn thông báo flash sau 5 giây
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });
});
