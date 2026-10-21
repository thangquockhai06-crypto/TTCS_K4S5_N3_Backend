from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.web_form import (
    PublicLeadSubmitRequest,
    PublicLeadSubmitResponse,
)
from app.services.web_form_service import web_form_service

router = APIRouter(prefix="/public/forms", tags=["Public Web-to-Lead Forms (SCRUM-24)"])


def _extract_client_ip(request: Request) -> str:
    """Trích xuất địa chỉ IP thực tế của client (hỗ trợ reverse proxy / Cloudflare / Nginx)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Nếu có nhiều IP do qua nhiều proxy, lấy IP đầu tiên
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


# ==============================================================================
# Public Web-to-Lead Endpoints (Không cần Token, Hỗ trợ Cross-Origin CORS)
# ==============================================================================

@router.options("/{form_key}/submit", summary="CORS Preflight cho Public Form Submit")
def options_form_submit(form_key: str):
    """Hỗ trợ CORS Preflight cho các website nhúng form từ domain bất kỳ."""
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Requested-With, Accept",
            "Access-Control-Max-Age": "86400",
        },
    )


@router.post(
    "/{form_key}/submit",
    response_model=PublicLeadSubmitResponse,
    summary="Tiếp nhận thông tin khách hàng từ biểu mẫu nhúng website (SCRUM-24)",
)
def submit_public_lead(
    form_key: str,
    payload: PublicLeadSubmitRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    API Công khai (Public API) tiếp nhận submit thông tin khách hàng tiềm năng:
    - Cho phép CORS từ mọi website bên ngoài.
    - Chống spam: Kiểm tra Honeypot (_hp) để loại bỏ bot spam tự động.
    - Giới hạn tần suất: Tối đa 5 lượt gửi / phút / địa chỉ IP Client (trả về 429 nếu vượt quá).
    - Tự động tạo Lead ở trạng thái 'NEW' và gắn đúng nguồn của biểu mẫu.
    """
    client_ip = _extract_client_ip(request)
    result = web_form_service.submit_lead_from_public_form(
        db=db,
        form_key=form_key,
        payload=payload,
        client_ip=client_ip,
    )

    # Đảm bảo header CORS luôn có mặt trong response
    response.headers["Access-Control-Allow-Origin"] = "*"
    return result


@router.get(
    "/{form_key}",
    summary="Lấy thông tin công khai của biểu mẫu theo form_key (SCRUM-24)",
)
def get_public_form_info(
    form_key: str,
    response: Response,
    db: Session = Depends(get_db),
):
    """Lấy thông tin tiêu đề và trạng thái của biểu mẫu để hiển thị trên website."""
    form = web_form_service.get_form_by_key(db=db, form_key=form_key)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return {
        "name": form.name,
        "lead_source": form.lead_source,
        "is_active": form.is_active,
    }


@router.get(
    "/{form_key}/render",
    response_class=HTMLResponse,
    summary="Giao diện biểu mẫu nhúng độc lập / Iframe (SCRUM-24)",
)
def render_iframe_form(
    form_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Trả về trang HTML hoàn chỉnh cho biểu mẫu nhúng (dùng cho Iframe hoặc hiển thị trực tiếp).
    Có sẵn thiết kế hiện đại, chống spam honeypot và xử lý Ajax submit mượt mà.
    """
    form = web_form_service.get_form_by_key(db=db, form_key=form_key)
    base_url = str(request.base_url).rstrip("/")
    submit_url = f"{base_url}/api/v1/public/forms/{form_key}/submit"

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{form.name} - NexusCRM</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #ffffff;
            --text-main: #0f172a;
            --text-sub: #475569;
            --border: #cbd5e1;
            --border-focus: #3b82f6;
            --danger: #dc2626;
            --success: #16a34a;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: transparent; padding: 16px; color: var(--text-main); font-size: 14px; }}
        .form-card {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            max-width: 540px;
            margin: 0 auto;
        }}
        .form-title {{ font-size: 1.25rem; font-weight: 700; color: var(--text-main); margin-bottom: 6px; }}
        .form-desc {{ font-size: 0.875rem; color: var(--text-sub); margin-bottom: 20px; line-height: 1.4; }}
        .form-group {{ margin-bottom: 16px; }}
        .form-label {{ display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.85rem; color: #1e293b; }}
        .form-label span.req {{ color: var(--danger); margin-left: 2px; }}
        .form-control {{
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.15s, box-shadow 0.15s;
        }}
        .form-control:focus {{
            border-color: var(--border-focus);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18);
        }}
        textarea.form-control {{ resize: vertical; min-height: 72px; }}
        /* Honeypot field - Luôn ẩn khỏi tầm nhìn người dùng thực tế */
        .hp-field {{ display: none !important; position: absolute !important; left: -9999px !important; }}
        .btn-submit {{
            width: 100%;
            padding: 12px 20px;
            background: var(--primary);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s, transform 0.05s;
        }}
        .btn-submit:hover {{ background: var(--primary-hover); }}
        .btn-submit:active {{ transform: scale(0.99); }}
        .btn-submit:disabled {{ background: #94a3b8; cursor: not-allowed; }}
        .alert {{
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-bottom: 16px;
            display: none;
            line-height: 1.4;
        }}
        .alert-success {{ background: #dcfce7; color: var(--success); border: 1px solid #bbf7d0; }}
        .alert-error {{ background: #fee2e2; color: var(--danger); border: 1px solid #fecaca; }}
    </style>
</head>
<body>
    <div class="form-card">
        <h2 class="form-title">{form.name}</h2>
        <p class="form-desc">Vui lòng để lại thông tin liên hệ. Chuyên viên của chúng tôi sẽ tư vấn và hỗ trợ bạn trong thời gian sớm nhất.</p>

        <div id="form-alert-success" class="alert alert-success"></div>
        <div id="form-alert-error" class="alert alert-error"></div>

        <form id="nexus-lead-form" onsubmit="handleFormSubmit(event)">
            <!-- Honeypot Field Chống bot spam -->
            <div class="hp-field" aria-hidden="true">
                <input type="text" name="_hp" tabindex="-1" autocomplete="off" />
                <input type="text" name="website_hp" tabindex="-1" autocomplete="off" />
            </div>

            <div class="form-group">
                <label class="form-label" for="full_name">Họ và tên <span class="req">*</span></label>
                <input type="text" id="full_name" name="full_name" class="form-control" placeholder="Ví dụ: Nguyễn Văn An" required minlength="2" />
            </div>

            <div class="form-group">
                <label class="form-label" for="email">Địa chỉ Email <span class="req">*</span></label>
                <input type="email" id="email" name="email" class="form-control" placeholder="name@company.com" required />
            </div>

            <div class="form-group">
                <label class="form-label" for="phone">Số điện thoại liên hệ <span class="req">*</span></label>
                <input type="tel" id="phone" name="phone" class="form-control" placeholder="Ví dụ: 0912345678" required pattern="^(03|05|07|08|09)\\d{{8}}$" title="Vui lòng nhập số điện thoại di động Việt Nam (10 số, bắt đầu bằng 03, 05, 07, 08 hoặc 09)" />
            </div>

            <div class="form-group">
                <label class="form-label" for="company">Tên công ty / Tổ chức</label>
                <input type="text" id="company" name="company" class="form-control" placeholder="Ví dụ: Công ty TNHH Giải Pháp Số" />
            </div>

            <div class="form-group">
                <label class="form-label" for="interest_need">Nhu cầu quan tâm / Lời nhắn</label>
                <textarea id="interest_need" name="interest_need" class="form-control" placeholder="Mô tả nhu cầu tư vấn phần mềm CRM hoặc giải pháp của bạn..."></textarea>
            </div>

            <button type="submit" id="submit-btn" class="btn-submit">Gửi thông tin tư vấn</button>
        </form>
    </div>

    <script>
        async function handleFormSubmit(e) {{
            e.preventDefault();
            const form = e.target;
            const submitBtn = document.getElementById('submit-btn');
            const alertSuccess = document.getElementById('form-alert-success');
            const alertError = document.getElementById('form-alert-error');

            alertSuccess.style.display = 'none';
            alertError.style.display = 'none';
            submitBtn.disabled = true;
            submitBtn.innerText = 'Đang xử lý...';

            const payload = {{
                full_name: form.full_name.value.trim(),
                email: form.email.value.trim(),
                phone: form.phone.value.trim(),
                company: form.company.value.trim() || null,
                interest_need: form.interest_need.value.trim() || null,
                _hp: form._hp.value || null,
                website_hp: form.website_hp.value || null
            }};

            try {{
                const res = await fetch('{submit_url}', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});

                const data = await res.json();
                if (res.ok) {{
                    alertSuccess.innerText = data.message || 'Gửi thông tin thành công!';
                    alertSuccess.style.display = 'block';
                    form.reset();
                }} else {{
                    const err = data.detail || 'Không thể gửi biểu mẫu. Vui lòng kiểm tra lại thông tin.';
                    alertError.innerText = err;
                    alertError.style.display = 'block';
                }}
            }} catch (err) {{
                alertError.innerText = 'Lỗi kết nối máy chủ. Vui lòng thử lại sau.';
                alertError.style.display = 'block';
            }} finally {{
                submitBtn.disabled = false;
                submitBtn.innerText = 'Gửi thông tin tư vấn';
            }}
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@router.get(
    "/loader.js",
    summary="Tải mã nhúng Javascript cho biểu mẫu (SCRUM-24)",
)
def get_form_loader_script(request: Request):
    """
    Trả về tệp script JS `form-loader.js` để tự động render biểu mẫu vào container
    `<div id="crm-lead-form" data-form-key="YOUR_FORM_KEY"></div>`.
    """
    base_url = str(request.base_url).rstrip("/")
    js_content = f"""/**
 * NexusCRM Web-to-Lead Form Loader (SCRUM-24)
 * Tự động tạo và nhúng biểu mẫu thu thập lead an toàn vào website khách hàng.
 */
(function() {{
    const container = document.getElementById('crm-lead-form');
    if (!container) return;

    let formKey = container.getAttribute('data-form-key');
    if (!formKey) {{
        const scriptTag = document.querySelector('script[data-form-key]');
        if (scriptTag) formKey = scriptTag.getAttribute('data-form-key');
    }}
    if (!formKey) return;

    const endpointUrl = '{base_url}/api/v1/public/forms/' + formKey + '/submit';
    const iframeUrl = '{base_url}/api/v1/public/forms/' + formKey + '/render';

    // Tạo iframe an toàn và tương thích
    const iframe = document.createElement('iframe');
    iframe.src = iframeUrl;
    iframe.width = '100%';
    iframe.height = '580';
    iframe.style.border = 'none';
    iframe.style.maxWidth = '640px';
    iframe.style.display = 'block';
    iframe.style.margin = '0 auto';
    iframe.setAttribute('title', 'NexusCRM Lead Capture Form');

    container.innerHTML = '';
    container.appendChild(iframe);
}})();"""
    return Response(content=js_content, media_type="application/javascript")
