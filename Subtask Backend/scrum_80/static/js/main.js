/**
 * CLIENT-SIDE INTERACTIVITY - SCRUM-80
 * Kiểm tra định dạng số điện thoại Việt Nam theo thời gian thực & Live Preview chữ ký email
 */

function initProfilePage() {
  const nameInput = document.getElementById("full_name");
  const phoneInput = document.getElementById("phone");
  const signatureTextarea = document.getElementById("email_signature");
  
  const phoneBadge = document.getElementById("phoneStatusBadge");
  const phoneFeedback = document.getElementById("phoneFeedback");
  const signaturePreview = document.getElementById("signatureLivePreview");
  const senderPreview = document.getElementById("previewSender");
  const charCount = document.getElementById("signatureCharCount");
  const btnAutoGenerate = document.getElementById("btnAutoGenerateSignature");
  
  const emailInput = document.getElementById("email");
  const roleInput = document.getElementById("role_name");
  const groupInput = document.getElementById("business_group");

  // Regex kiểm tra số điện thoại di động Việt Nam chuẩn
  const VN_PHONE_REGEX = /^(?:\+?84|0)(3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9])[0-9]{7}$/;

  function cleanPhone(val) {
    return (val || "").replace(/[\s\.\-\(\)]+/g, "").trim();
  }

  // 1. Kiểm tra số điện thoại Việt Nam (Tiêu chí 3)
  function validatePhoneClient(phoneVal) {
    if (!phoneBadge || !phoneFeedback) return;
    
    const cleaned = cleanPhone(phoneVal);
    if (!cleaned) {
      phoneBadge.className = "phone-validation-badge invalid";
      phoneBadge.querySelector(".badge-text").textContent = "Chưa nhập";
      phoneFeedback.className = "field-feedback danger";
      phoneFeedback.textContent = "Vui lòng nhập số điện thoại di động Việt Nam.";
      return false;
    }

    if (VN_PHONE_REGEX.test(cleaned)) {
      phoneBadge.className = "phone-validation-badge valid";
      phoneBadge.querySelector(".badge-text").textContent = "✓ SĐT Việt Nam hợp lệ";
      phoneFeedback.className = "field-feedback success";
      phoneFeedback.textContent = "Số điện thoại đúng quy chuẩn mạng di động Việt Nam.";
      return true;
    } else {
      phoneBadge.className = "phone-validation-badge invalid";
      phoneBadge.querySelector(".badge-text").textContent = "✗ Sai định dạng";
      phoneFeedback.className = "field-feedback danger";
      
      const digits = cleaned.replace(/\D/g, "");
      if (digits.length < 10) {
        phoneFeedback.textContent = `Số quá ngắn (${digits.length}/10 số). Di động VN gồm 10 chữ số.`;
      } else if (digits.length > 11) {
        phoneFeedback.textContent = `Số quá dài (${digits.length} số). Vui lòng kiểm tra lại.`;
      } else {
        phoneFeedback.textContent = "Đầu số không khớp với các nhà mạng di động VN (03x, 05x, 07x, 08x, 09x).";
      }
      return false;
    }
  }

  // 2. Cập nhật xem trước Chữ ký Email theo thời gian thực
  function updateLiveSignature() {
    if (!signatureTextarea || !signaturePreview) return;
    
    const sigValue = signatureTextarea.value;
    signaturePreview.textContent = sigValue || "(Chưa có nội dung chữ ký email)";
    
    if (charCount) {
      charCount.textContent = `${sigValue.length} ký tự`;
    }
  }

  // 3. Cập nhật tên người gửi trên khung email mockup
  function updateSenderPreview() {
    if (!nameInput || !senderPreview || !emailInput) return;
    const currentName = nameInput.value.trim() || "Người dùng";
    const currentEmail = emailInput.value.trim();
    senderPreview.innerHTML = `<strong>${escapeHtml(currentName)}</strong> &lt;${escapeHtml(currentEmail)}&gt;`;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Gắn sự kiện lắng nghe
  if (phoneInput) {
    phoneInput.addEventListener("input", function() {
      validatePhoneClient(this.value);
    });
    // Kiểm tra ngay khi tải trang
    validatePhoneClient(phoneInput.value);
  }

  if (signatureTextarea) {
    signatureTextarea.addEventListener("input", function() {
      updateLiveSignature();
    });
    updateLiveSignature();
  }

  if (nameInput) {
    nameInput.addEventListener("input", function() {
      updateSenderPreview();
    });
  }

  // 4. Tính năng tự tạo mẫu chữ ký chuyên nghiệp
  if (btnAutoGenerate) {
    btnAutoGenerate.addEventListener("click", function() {
      const name = (nameInput ? nameInput.value : "").trim() || "Chuyên viên kinh doanh";
      const phone = (phoneInput ? phoneInput.value : "").trim() || "0912 345 678";
      const email = (emailInput ? emailInput.value : "").trim();
      const role = (roleInput ? roleInput.value : "").trim() || "Chuyên viên kinh doanh";
      const group = (groupInput ? groupInput.value : "").trim() || "Phòng Kinh Doanh";

      const template = 
`Trân trọng,
${name} | ${role}
${group} - Enterprise Solution Corp
Hotline/Zalo: ${phone} | Email: ${email}
Website: https://enterprise-solution.vn
Địa chỉ: Tòa nhà Landmark, Hà Nội`;

      if (signatureTextarea) {
        signatureTextarea.value = template;
        updateLiveSignature();
      }
    });
  }

  // 5. Cảnh báo an toàn nếu ai đó cố tình xóa thuộc tính readonly của các trường bị khóa
  const lockedInputs = document.querySelectorAll(".locked-input");
  lockedInputs.forEach(input => {
    input.addEventListener("keydown", function(e) {
      if (this.readOnly) {
        e.preventDefault();
      }
    });
  });
}

// Xử lý bật/tắt thanh Sidebar trên Mobile
document.addEventListener("DOMContentLoaded", function() {
  const toggleBtn = document.getElementById("btnToggleSidebar");
  const sidebar = document.getElementById("appSidebar");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", function(e) {
      e.stopPropagation();
      sidebar.classList.toggle("show");
    });

    document.addEventListener("click", function(e) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove("show");
      }
    });
  }
});
