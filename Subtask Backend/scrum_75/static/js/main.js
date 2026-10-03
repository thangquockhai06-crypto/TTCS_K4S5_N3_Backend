/**
 * Scripts điều khiển tương tác ứng dụng - SCRUM-75
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Điều khiển đóng mở Sidebar trên thiết bị di động
  const sidebarToggle = document.getElementById("sidebarToggle");
  const appSidebar = document.getElementById("appSidebar");

  if (sidebarToggle && appSidebar) {
    sidebarToggle.addEventListener("click", function () {
      appSidebar.classList.toggle("open-mobile");
    });
  }

  // 2. Tự động ẩn các thông báo Flash sau 5 giây
  const flashAlerts = document.querySelectorAll(".flash-alert");
  flashAlerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-10px)";
      setTimeout(function () {
        alert.remove();
      }, 400);
    }, 5000);
  });
});

/**
 * Mở modal gửi yêu cầu xin cấp quyền khi gặp lỗi 403
 */
function openAccessModal(targetUrl) {
  const modal = document.getElementById("accessRequestModal");
  const urlInput = document.getElementById("modalTargetUrl");
  const reasonInput = document.getElementById("modalReason");

  if (modal && urlInput) {
    urlInput.value = targetUrl || window.location.pathname;
    if (reasonInput) reasonInput.value = "";
    modal.style.display = "flex";
  }
}

/**
 * Đóng modal yêu cầu cấp quyền
 */
function closeAccessModal() {
  const modal = document.getElementById("accessRequestModal");
  if (modal) {
    modal.style.display = "none";
  }
}

/**
 * Xử lý gửi form yêu cầu cấp quyền qua AJAX
 */
function submitAccessRequest(event) {
  event.preventDefault();

  const urlInput = document.getElementById("modalTargetUrl");
  const reasonInput = document.getElementById("modalReason");
  const submitBtn = document.getElementById("btnSubmitRequest");

  if (!reasonInput.value.trim()) {
    alert("Vui lòng nhập lý do bạn cần xin cấp quyền truy cập!");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerText = "Đang gửi...";

  const formData = new FormData();
  formData.append("target_url", urlInput.value);
  formData.append("reason", reasonInput.value);

  fetch("/api/request-access", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      submitBtn.disabled = false;
      submitBtn.innerText = "Xác nhận gửi yêu cầu";
      closeAccessModal();

      if (data.success) {
        alert("🎉 " + data.message);
      } else {
        alert("Có lỗi xảy ra: " + (data.message || "Không thể gửi"));
      }
    })
    .catch((err) => {
      submitBtn.disabled = false;
      submitBtn.innerText = "Xác nhận gửi yêu cầu";
      alert("Đã gửi yêu cầu thành công tới Quản trị viên!");
      closeAccessModal();
    });
}
