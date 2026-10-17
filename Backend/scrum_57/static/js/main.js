// SCRUM-57 · Tự động áp dụng bộ lọc khi người dùng bật/tắt chip hoặc đổi thứ tự.
// Không có JS thì nút "Áp dụng" vẫn hoạt động bình thường.
document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("timeline-filter-form");
    if (!form) return;

    form.addEventListener("change", (event) => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement)) return;

        // Cập nhật trạng thái hiển thị ngay để phản hồi tức thì
        const chip = input.closest(".chip");
        if (chip) chip.classList.toggle("chip-on", input.checked);
        if (input.name === "order") {
            form.querySelectorAll(".order-toggle label").forEach((label) => {
                label.classList.toggle("active", label.contains(input));
            });
        }
        form.requestSubmit();
    });
});
