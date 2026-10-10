/**
 * AutoLead CRM - SCRUM-38: Chuyển Báo Giá thành Hợp Đồng
 * Frontend Scripts: Kiểm tra số HĐ duy nhất (AJAX Debounce), Date Validation, Simulator Runner
 */

document.addEventListener("DOMContentLoaded", function () {
    initContractNumberCheck();
    initDateValidation();
    initSimulatorRunner();
    initPrintContract();
});

/**
 * 1. TIÊU CHÍ 4: KIỂM TRA SỐ HỢP ĐỒNG DUY NHẤT (REALTIME AJAX DEBOUNCE)
 */
function initContractNumberCheck() {
    const input = document.getElementById("contract_number");
    const feedback = document.getElementById("contractNumberFeedback");
    const submitBtn = document.getElementById("btnSubmitConvert");
    const quickFillBtn = document.getElementById("btnQuickFill");

    if (!input || !feedback) return;

    let debounceTimer = null;

    function checkNumber(value) {
        const trimmed = value.trim();
        if (!trimmed) {
            feedback.innerHTML = '<span class="feedback-error">⚠️ Vui lòng nhập số hợp đồng (bắt buộc).</span>';
            if (submitBtn) submitBtn.disabled = true;
            return;
        }

        feedback.innerHTML = '<span style="color: #64748b;">⏳ Đang kiểm tra tính duy nhất của số hợp đồng...</span>';

        fetch(`/api/contracts/check-number?number=${encodeURIComponent(trimmed)}`)
            .then(res => res.json())
            .then(data => {
                if (data.available) {
                    feedback.innerHTML = `<span class="feedback-success">✓ ${data.message}</span>`;
                    input.style.borderColor = "var(--success)";
                    if (submitBtn) submitBtn.disabled = false;
                } else {
                    feedback.innerHTML = `<span class="feedback-error">❌ ${data.message}</span>`;
                    input.style.borderColor = "var(--danger)";
                    if (submitBtn) submitBtn.disabled = true;
                }
            })
            .catch(err => {
                console.error("Lỗi kiểm tra số HĐ:", err);
                feedback.innerHTML = '';
            });
    }

    input.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            checkNumber(this.value);
        }, 300);
    });

    if (quickFillBtn) {
        quickFillBtn.addEventListener("click", function () {
            const suggested = this.getAttribute("data-suggested");
            if (suggested) {
                input.value = suggested;
                checkNumber(suggested);
            }
        });
    }

    // Kiểm tra ngay khi tải trang nếu đã có giá trị
    if (input.value) {
        checkNumber(input.value);
    }
}

/**
 * 2. TIÊU CHÍ 2: KIỂM TRA LOGIC NGÀY THÁNG (NGÀY HIỆU LỰC <= NGÀY HẾT HẠN)
 */
function initDateValidation() {
    const effInput = document.getElementById("effective_date");
    const expInput = document.getElementById("expiration_date");
    const dateFeedback = document.getElementById("dateFeedback");

    if (!effInput || !expInput || !dateFeedback) return;

    function validateDates() {
        const effVal = effInput.value;
        const expVal = expInput.value;

        if (effVal && expVal) {
            const dEff = new Date(effVal);
            const dExp = new Date(expVal);

            if (dEff > dExp) {
                dateFeedback.innerHTML = '<span class="feedback-error">❌ Ngày hiệu lực không được sau ngày hết hạn hợp đồng!</span>';
                expInput.style.borderColor = "var(--danger)";
                return false;
            } else {
                dateFeedback.innerHTML = '<span class="feedback-success">✓ Thời hạn hợp đồng hợp lệ.</span>';
                expInput.style.borderColor = "var(--border-color)";
                return true;
            }
        }
        dateFeedback.innerHTML = '';
        return true;
    }

    effInput.addEventListener("change", validateDates);
    expInput.addEventListener("change", validateDates);
}

/**
 * 3. TRÌNH KIỂM THỬ TỰ ĐỘNG 4 TIÊU CHÍ (SIMULATOR RUNNER)
 */
function initSimulatorRunner() {
    const runBtn = document.getElementById("btnRunSimulator");
    const resultsContainer = document.getElementById("simulatorResults");
    const statusBanner = document.getElementById("simulatorStatus");

    if (!runBtn || !resultsContainer) return;

    runBtn.addEventListener("click", function () {
        runBtn.disabled = true;
        runBtn.innerHTML = "⏳ Đang chạy kiểm thử 4 tiêu chí...";
        resultsContainer.innerHTML = '<div style="text-align: center; padding: 30px; color: #64748b;">Đang khởi tạo môi trường và thực thi kiểm thử Invariant AC1, AC2, AC3, AC4...</div>';

        fetch("/api/simulator/run-all", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        })
            .then(res => res.json())
            .then(data => {
                runBtn.disabled = false;
                runBtn.innerHTML = "⚡ Chạy Lại Kiểm Thử (1-Click Run)";

                if (data.success) {
                    renderSimulatorResults(data, resultsContainer, statusBanner);
                } else {
                    resultsContainer.innerHTML = `<div class="alert alert-error">Lỗi thực thi kiểm thử: ${data.message}</div>`;
                }
            })
            .catch(err => {
                runBtn.disabled = false;
                runBtn.innerHTML = "⚡ Chạy Lại Kiểm Thử (1-Click Run)";
                resultsContainer.innerHTML = `<div class="alert alert-error">Lỗi kết nối máy chủ: ${err}</div>`;
            });
    });
}

function renderSimulatorResults(data, container, statusBanner) {
    let html = "";
    const allPassed = data.all_passed;

    if (statusBanner) {
        statusBanner.style.display = "block";
        if (allPassed) {
            statusBanner.className = "alert alert-success";
            statusBanner.innerHTML = `<strong>🎉 XUẤT SẮC! TOÀN BỘ 4 TIÊU CHÍ CHẤP NHẬN ĐẠT 100%</strong> - Hệ thống đảm bảo an toàn nghiệp vụ Kế toán & đồng bộ Cơ hội CRM tuyệt đối.`;
        } else {
            statusBanner.className = "alert alert-error";
            statusBanner.innerHTML = `<strong>⚠️ CÓ TIÊU CHÍ CHƯA ĐẠT</strong> - Vui lòng kiểm tra chi tiết lỗi bên dưới.`;
        }
    }

    data.results.forEach(res => {
        const passClass = res.passed ? "test-pass" : "test-fail";
        const badgeText = res.passed ? "✓ ĐẠT 100%" : "❌ THẤT BẠI";
        const icon = res.passed ? "🟢" : "🔴";

        html += `
            <div class="test-result-item ${passClass}">
                <div style="font-size: 24px; margin-top: 2px;">${icon}</div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <h4 style="font-size: 14.5px; font-weight: 700; color: var(--text-main);">${res.title}</h4>
                        <span class="test-status-badge">${badgeText}</span>
                    </div>
                    <p style="font-size: 13.5px; color: #475569; line-height: 1.5; margin: 0;">${res.detail}</p>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 4. NÚT IN HỢP ĐỒNG (PRINT CONTRACT PREVIEW)
 */
function initPrintContract() {
    const printBtn = document.getElementById("btnPrintContract");
    if (printBtn) {
        printBtn.addEventListener("click", function () {
            window.print();
        });
    }
}
