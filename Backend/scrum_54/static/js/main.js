/**
 * AutoLead CRM - Ticket SCRUM-54
 * Client-Side JavaScript
 */

document.addEventListener("DOMContentLoaded", () => {
    // Tự động ẩn thông báo Flash sau 6 giây
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // Xác nhận khi thực hiện chuyển đổi Lead (1-Click Convert)
    const convertForms = document.querySelectorAll(".form-confirm-convert");
    convertForms.forEach((form) => {
        form.addEventListener("submit", (e) => {
            const confirmed = confirm(
                "🚀 XÁC NHẬN CHUYỂN ĐỔI LEAD?\n\n" +
                "• Thao tác sẽ đồng thời sinh: Khách hàng doanh nghiệp, Người liên hệ và Cơ hội bán hàng.\n" +
                "• Toàn bộ lịch sử hoạt động sẽ được chuyển sang Khách hàng mới.\n" +
                "• Lead sẽ chuyển sang trạng thái ĐÃ CHUYỂN ĐỔI và BỊ KHÓA VĨNH VIỄN không thể sửa nữa.\n\n" +
                "Bạn có chắc chắn muốn tiếp tục?"
            );
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // Format input số tiền theo thời gian thực (nếu có trường nhập tiền)
    const currencyInputs = document.querySelectorAll(".input-currency");
    currencyInputs.forEach((input) => {
        input.addEventListener("input", (e) => {
            let val = e.target.value.replace(/\D/g, "");
            if (val) {
                e.target.value = new Intl.NumberFormat("vi-VN").format(val);
            }
        });
    });
});
