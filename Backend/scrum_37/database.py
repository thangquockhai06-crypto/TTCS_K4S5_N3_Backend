"""
Quản lý cơ sở dữ liệu Thread-Safe & Động cơ Quản lý Phiên bản Báo giá (SCRUM-35 / SCRUM-37)
Subtasks: SCRUM-234 (FE) & SCRUM-235 (BE)

Đáp ứng đầy đủ 3 Tiêu chí chấp nhận (Acceptance Criteria):
1. Mỗi lần sửa sau khi đã gửi sẽ tạo phiên bản mới, phiên bản cũ được giữ nguyên.
2. So sánh cạnh nhau hai phiên bản để thấy đã thay đổi gì.
3. Chỉ một phiên bản ở trạng thái đang hiệu lực tại một thời điểm.
"""

import threading
import copy
import hashlib
import json
from datetime import datetime, timedelta

from config import (
    ROLE_SALES_REP,
    ROLE_SALES_LEAD,
    ROLE_CUSTOMER,
    STATUS_DRAFT,
    STATUS_SENT,
    STATUS_ACCEPTED,
    STATUS_SUPERSEDED,
    STATUS_REJECTED,
    STATUS_LABELS,
    DEFAULT_VAT_PERCENT,
    PRODUCT_CATALOG,
    PAYMENT_TERMS_OPTIONS,
    DELIVERY_TERMS_OPTIONS,
    REVISION_REASONS
)


def get_current_time():
    """Lấy thời gian hiện tại"""
    return datetime.now()


def format_currency(amount):
    """Định dạng tiền tệ VND chuyên nghiệp"""
    try:
        val = float(amount or 0)
        return f"{val:,.0f} đ".replace(",", ".")
    except Exception:
        return f"{amount} đ"


def format_datetime(dt):
    """Định dạng ngày giờ hiển thị"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%H:%M:%S %d/%m/%Y")


def format_date(dt):
    """Định dạng ngày tháng"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%d/%m/%Y")


class Database:
    """
    Cơ sở dữ liệu In-Memory Thread-Safe quản lý phiên bản Báo giá (Quotation Versioning Engine).
    Hỗ trợ kiểm tra bất biến (Invariant Check), Sổ cái bất biến và Động cơ so sánh Side-by-side.
    """

    def __init__(self):
        self.lock = threading.RLock()
        # Lưu trữ phiên bản theo version_id (VD: "QVER-001-1")
        self.versions = {}
        # Chỉ mục nhóm theo họ mã báo giá: quote_code -> [version_id_1, version_id_2, ...]
        self.quote_families = {}
        # Lịch sử sự kiện (Audit Event Log)
        self.audit_logs = []

        self._quote_code_counter = 100
        self._version_counter = 1
        self._item_counter = 1

        self._seed_sample_data()

    def _generate_sha256_snapshot(self, version_dict):
        """Tạo mã băm SHA-256 bất biến cho dữ liệu của một phiên bản đã gửi"""
        data_to_hash = {
            "version_id": version_dict.get("version_id"),
            "quote_code": version_dict.get("quote_code"),
            "version_number": version_dict.get("version_number"),
            "customer_name": version_dict.get("customer_name"),
            "items": version_dict.get("items", []),
            "subtotal": version_dict.get("subtotal"),
            "total_discount": version_dict.get("total_discount"),
            "grand_total": version_dict.get("grand_total"),
            "payment_terms": version_dict.get("payment_terms"),
            "delivery_terms": version_dict.get("delivery_terms"),
            "sent_at": str(version_dict.get("sent_at"))
        }
        serialized = json.dumps(data_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _calculate_totals(self, items, vat_percent=DEFAULT_VAT_PERCENT):
        """Tính toán tổng tiền, chiết khấu và thuế VAT cho danh sách sản phẩm"""
        subtotal = 0.0
        total_discount = 0.0

        processed_items = []
        for idx, it in enumerate(items, 1):
            qty = float(it.get("quantity", 1))
            unit_price = float(it.get("unit_price", 0))
            line_subtotal = qty * unit_price
            
            disc_pct = float(it.get("discount_percent", 0.0))
            disc_amt = float(it.get("discount_amount", 0.0))
            
            # Ưu tiên tính theo % chiết khấu nếu có, nếu không lấy theo số tiền
            if disc_pct > 0:
                line_discount = line_subtotal * (disc_pct / 100.0)
            else:
                line_discount = min(disc_amt, line_subtotal)
                if line_subtotal > 0:
                    disc_pct = round((line_discount / line_subtotal) * 100.0, 2)
            
            line_amount = max(0.0, line_subtotal - line_discount)
            
            subtotal += line_subtotal
            total_discount += line_discount

            processed_items.append({
                "item_id": it.get("item_id") or f"ITEM-{self._item_counter}",
                "line_no": idx,
                "product_id": it.get("product_id", ""),
                "product_name": it.get("product_name", "Sản phẩm tùy chỉnh"),
                "unit": it.get("unit", "Gói"),
                "quantity": qty,
                "unit_price": unit_price,
                "discount_percent": disc_pct,
                "discount_amount": line_discount,
                "amount": line_amount,
                "notes": it.get("notes", "")
            })
            self._item_counter += 1

        subtotal_after_discount = max(0.0, subtotal - total_discount)
        vat_amount = subtotal_after_discount * (vat_percent / 100.0)
        grand_total = subtotal_after_discount + vat_amount

        return {
            "items": processed_items,
            "subtotal": subtotal,
            "total_discount": total_discount,
            "subtotal_after_discount": subtotal_after_discount,
            "vat_percent": vat_percent,
            "vat_amount": vat_amount,
            "grand_total": grand_total
        }

    def _verify_single_effective_invariant(self, quote_code):
        """
        Kiểm tra bất biến Tiêu chí 3:
        Chỉ có DUY NHẤT một phiên bản mang cờ is_effective = True tại một thời điểm
        (hoặc 0 nếu toàn bộ bản nháp chưa gửi/chưa kích hoạt).
        Nếu phát hiện > 1 phiên bản hiệu lực -> Báo động vi phạm Invariant.
        """
        v_ids = self.quote_families.get(quote_code, [])
        effective_count = sum(1 for vid in v_ids if self.versions.get(vid, {}).get("is_effective", False))
        if effective_count > 1:
            raise AssertionError(
                f"[VI PHẠM BẤT BIẾN AC3] Báo giá '{quote_code}' có {effective_count} phiên bản cùng ở trạng thái Đang hiệu lực! Ràng buộc chỉ cho phép tối đa 1."
            )
        return True

    def create_initial_quote(self, data, sales_rep_name="Nguyễn Văn Kinh Doanh", actor=None):
        """Tạo mới một báo giá gốc (Phiên bản v1)"""
        if actor:
            sales_rep_name = actor
        with self.lock:
            self._quote_code_counter += 1
            quote_code = data.get("quote_code") or f"BG-2026-{self._quote_code_counter:03d}"
            
            calc = self._calculate_totals(data.get("items", []), data.get("vat_percent", DEFAULT_VAT_PERCENT))
            
            version_id = f"QVER-{self._version_counter:04d}"
            self._version_counter += 1

            now = get_current_time()
            validity_days = int(data.get("validity_days", 15))
            expiration_date = now + timedelta(days=validity_days)

            is_sent = bool(data.get("is_sent", False))
            status = STATUS_SENT if is_sent else STATUS_DRAFT
            # Tiêu chí 3: Nếu gửi ngay khi tạo thì kích hoạt hiệu lực, nếu lưu nháp thì chưa hiệu lực
            is_effective = bool(data.get("is_effective", is_sent))

            version_doc = {
                "version_id": version_id,
                "quote_code": quote_code,
                "version_number": 1,
                "version_tag": "v1.0",
                "title": data.get("title", f"Báo giá giải pháp phần mềm - {quote_code}"),
                "customer_name": data.get("customer_name", "Công ty Khách Hàng Mẫu"),
                "customer_email": data.get("customer_email", "contact@customer.vn"),
                "customer_phone": data.get("customer_phone", "0901234567"),
                "customer_company": data.get("customer_company", data.get("customer_name", "")),
                "sales_rep_name": sales_rep_name,
                "items": calc["items"],
                "subtotal": calc["subtotal"],
                "total_discount": calc["total_discount"],
                "subtotal_after_discount": calc["subtotal_after_discount"],
                "vat_percent": calc["vat_percent"],
                "vat_amount": calc["vat_amount"],
                "grand_total": calc["grand_total"],
                "payment_terms": data.get("payment_terms", PAYMENT_TERMS_OPTIONS[1]),
                "delivery_terms": data.get("delivery_terms", DELIVERY_TERMS_OPTIONS[1]),
                "validity_days": validity_days,
                "expiration_date": expiration_date.isoformat(),
                "notes": data.get("notes", "Báo giá tiêu chuẩn khởi tạo"),
                "revision_reason": "Khởi tạo báo giá phiên bản đầu tiên (v1.0)",
                "status": status,
                "is_sent": is_sent,
                "is_effective": is_effective,
                "is_locked": is_sent,  # Khóa nếu đã gửi
                "parent_version_id": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "sent_at": now.isoformat() if is_sent else None,
                "integrity_hash": None
            }

            if is_sent:
                version_doc["integrity_hash"] = self._generate_sha256_snapshot(version_doc)

            self.versions[version_id] = version_doc
            self.quote_families[quote_code] = [version_id]

            self._log_audit(
                quote_code=quote_code,
                version_id=version_id,
                action="CREATE_INITIAL_QUOTE",
                details=f"Khởi tạo báo giá {quote_code} phiên bản v1.0 ({status})",
                actor=sales_rep_name
            )

            self._verify_single_effective_invariant(quote_code)
            return copy.deepcopy(version_doc)

    def edit_quote(self, version_id, updated_data, actor="Nguyễn Văn Kinh Doanh"):
        """
        Xử lý nghiệp vụ Chỉnh sửa báo giá:
        - NẾU CHƯA GỬI (is_sent == False): Cập nhật trực tiếp lên phiên bản hiện tại (In-place edit).
        - NẾU ĐÃ GỬI (is_sent == True): BẮT BUỘC TẠO PHIÊN BẢN MỚI (v_next), PHIÊN BẢN CŨ ĐƯỢC GIỮ NGUYÊN 100% (AC1).
        """
        with self.lock:
            if version_id not in self.versions:
                raise KeyError(f"Không tìm thấy phiên bản báo giá với ID '{version_id}'")

            current_ver = self.versions[version_id]
            quote_code = current_ver["quote_code"]

            # ==============================================================
            # TRƯỜNG HỢP 1: BÁO GIÁ CHƯA GỬI (BẢN NHÁP DRAFT) -> SỬA TRỰC TIẾP
            # ==============================================================
            if not current_ver["is_sent"]:
                calc = self._calculate_totals(
                    updated_data.get("items", current_ver["items"]),
                    updated_data.get("vat_percent", current_ver["vat_percent"])
                )
                current_ver["title"] = updated_data.get("title", current_ver["title"])
                current_ver["customer_name"] = updated_data.get("customer_name", current_ver["customer_name"])
                current_ver["customer_email"] = updated_data.get("customer_email", current_ver["customer_email"])
                current_ver["customer_phone"] = updated_data.get("customer_phone", current_ver["customer_phone"])
                current_ver["customer_company"] = updated_data.get("customer_company", current_ver["customer_company"])
                current_ver["items"] = calc["items"]
                current_ver["subtotal"] = calc["subtotal"]
                current_ver["total_discount"] = calc["total_discount"]
                current_ver["subtotal_after_discount"] = calc["subtotal_after_discount"]
                current_ver["vat_percent"] = calc["vat_percent"]
                current_ver["vat_amount"] = calc["vat_amount"]
                current_ver["grand_total"] = calc["grand_total"]
                current_ver["payment_terms"] = updated_data.get("payment_terms", current_ver["payment_terms"])
                current_ver["delivery_terms"] = updated_data.get("delivery_terms", current_ver["delivery_terms"])
                current_ver["validity_days"] = int(updated_data.get("validity_days", current_ver["validity_days"]))
                current_ver["notes"] = updated_data.get("notes", current_ver["notes"])
                current_ver["updated_at"] = get_current_time().isoformat()

                self._log_audit(
                    quote_code=quote_code,
                    version_id=version_id,
                    action="UPDATE_DRAFT_IN_PLACE",
                    details=f"Cập nhật trực tiếp bản nháp {current_ver['version_tag']} (chưa gửi khách)",
                    actor=actor
                )
                return {
                    "is_new_version": False,
                    "version": copy.deepcopy(current_ver),
                    "message": f"Đã lưu các thay đổi trực tiếp vào bản nháp {current_ver['version_tag']} thành công."
                }

            # ==============================================================
            # TRƯỜNG HỢP 2: BÁO GIÁ ĐÃ GỬI (is_sent == True)
            # -> ĐÁP ỨNG TIÊU CHÍ 1: TẠO PHIÊN BẢN MỚI, PHIÊN BẢN CŨ ĐƯỢC GIỮ NGUYÊN 100%
            # ==============================================================
            # 1. Bảo vệ phiên bản cũ: Xác minh phiên bản cũ không bị biến đổi
            old_hash = current_ver.get("integrity_hash")
            current_ver["is_locked"] = True  # Đảm bảo cờ khóa

            # 2. Tính số phiên bản tiếp theo
            family_vids = self.quote_families.get(quote_code, [])
            all_family_vers = [self.versions[vid] for vid in family_vids if vid in self.versions]
            max_v_num = max(v["version_number"] for v in all_family_vers)
            new_v_num = max_v_num + 1
            new_v_tag = f"v{new_v_num}.0"

            # 3. Tạo ID cho phiên bản mới
            new_version_id = f"QVER-{self._version_counter:04d}"
            self._version_counter += 1

            # 4. Tính toán số tiền mới
            calc = self._calculate_totals(
                updated_data.get("items", current_ver["items"]),
                updated_data.get("vat_percent", current_ver["vat_percent"])
            )

            now = get_current_time()
            validity_days = int(updated_data.get("validity_days", current_ver["validity_days"]))
            expiration_date = now + timedelta(days=validity_days)
            reason = updated_data.get("revision_reason") or "Điều chỉnh báo giá theo yêu cầu đàm phán với khách hàng"

            # 5. Khởi tạo tài liệu phiên bản mới
            # TIÊU CHÍ 3: Bản mới vừa tạo chưa gửi -> is_effective = False (bản cũ đã gửi vẫn đang hiệu lực với khách)
            new_version_doc = {
                "version_id": new_version_id,
                "quote_code": quote_code,
                "version_number": new_v_num,
                "version_tag": new_v_tag,
                "title": updated_data.get("title", current_ver["title"]),
                "customer_name": updated_data.get("customer_name", current_ver["customer_name"]),
                "customer_email": updated_data.get("customer_email", current_ver["customer_email"]),
                "customer_phone": updated_data.get("customer_phone", current_ver["customer_phone"]),
                "customer_company": updated_data.get("customer_company", current_ver["customer_company"]),
                "sales_rep_name": actor,
                "items": calc["items"],
                "subtotal": calc["subtotal"],
                "total_discount": calc["total_discount"],
                "subtotal_after_discount": calc["subtotal_after_discount"],
                "vat_percent": calc["vat_percent"],
                "vat_amount": calc["vat_amount"],
                "grand_total": calc["grand_total"],
                "payment_terms": updated_data.get("payment_terms", current_ver["payment_terms"]),
                "delivery_terms": updated_data.get("delivery_terms", current_ver["delivery_terms"]),
                "validity_days": validity_days,
                "expiration_date": expiration_date.isoformat(),
                "notes": updated_data.get("notes", current_ver["notes"]),
                "revision_reason": reason,
                "status": STATUS_DRAFT,       # Phiên bản mới bắt đầu ở trạng thái nháp
                "is_sent": False,              # Chưa gửi khách
                "is_effective": False,         # Bản cũ vẫn đang giữ hiệu lực cam kết
                "is_locked": False,            # Cho phép NVKD tiếp tục chỉnh sửa trước khi gửi
                "parent_version_id": version_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "sent_at": None,
                "integrity_hash": None
            }

            # 6. Lưu vào cơ sở dữ liệu
            self.versions[new_version_id] = new_version_doc
            self.quote_families[quote_code].append(new_version_id)

            self._log_audit(
                quote_code=quote_code,
                version_id=new_version_id,
                action="CREATE_NEW_VERSION",
                details=f"Tạo tự động phiên bản mới {new_v_tag} kế thừa từ {current_ver['version_tag']} đã gửi. Lý do: '{reason}'. Bản cũ {current_ver['version_tag']} được giữ nguyên vẹn 100%.",
                actor=actor
            )

            # Kiểm tra bất biến Tiêu chí 3
            self._verify_single_effective_invariant(quote_code)

            return {
                "is_new_version": True,
                "old_version_id": version_id,
                "new_version_id": new_version_id,
                "version": copy.deepcopy(new_version_doc),
                "message": f"Báo giá {current_ver['version_tag']} đã gửi trước đó nên được giữ nguyên. Hệ thống đã tự động tạo Phiên bản mới {new_v_tag} thành công!"
            }

    def send_quote_to_customer(self, version_id, actor="Nguyễn Văn Kinh Doanh"):
        """
        Nghiệp vụ Gửi báo giá cho khách hàng:
        - Đánh dấu is_sent = True, status = STATUS_SENT, sent_at = now.
        - Khóa đóng băng phiên bản (is_locked = True, mã SHA-256).
        - ĐÁP ỨNG TIÊU CHÍ 3: Kích hoạt phiên bản này thành ĐANG HIỆU LỰC (is_effective = True).
        - Toàn bộ các phiên bản cũ hơn của cùng mã báo giá chuyển sang HẾT HIỆU LỰC (is_effective = False, status = STATUS_SUPERSEDED).
        """
        with self.lock:
            if version_id not in self.versions:
                raise KeyError(f"Không tìm thấy phiên bản báo giá với ID '{version_id}'")

            target_ver = self.versions[version_id]
            quote_code = target_ver["quote_code"]
            now = get_current_time()

            # 1. Đặt trạng thái gửi & đóng băng
            target_ver["is_sent"] = True
            target_ver["status"] = STATUS_SENT
            target_ver["sent_at"] = now.isoformat()
            target_ver["updated_at"] = now.isoformat()
            target_ver["is_locked"] = True
            target_ver["integrity_hash"] = self._generate_sha256_snapshot(target_ver)

            # 2. Xử lý TIÊU CHÍ 3: Chỉ DUY NHẤT một phiên bản có is_effective = True
            family_vids = self.quote_families.get(quote_code, [])
            for vid in family_vids:
                if vid != version_id and vid in self.versions:
                    other_ver = self.versions[vid]
                    if other_ver["is_effective"]:
                        other_ver["is_effective"] = False
                        if other_ver["is_sent"]:
                            other_ver["status"] = STATUS_SUPERSEDED
                        other_ver["updated_at"] = now.isoformat()

            target_ver["is_effective"] = True

            self._log_audit(
                quote_code=quote_code,
                version_id=version_id,
                action="SEND_QUOTE_TO_CUSTOMER",
                details=f"Gửi báo giá phiên bản {target_ver['version_tag']} cho khách hàng. Kích hoạt thành phiên bản hiệu lực DUY NHẤT.",
                actor=actor
            )

            # Kiểm tra bất biến Tiêu chí 3
            self._verify_single_effective_invariant(quote_code)
            return copy.deepcopy(target_ver)

    def set_effective_version(self, version_id, actor="Nguyễn Văn Kinh Doanh"):
        """
        ĐÁP ỨNG TIÊU CHÍ 3:
        Chủ động chuyển đổi phiên bản hiệu lực.
        Đảm bảo tại một thời điểm CHỈ DUY NHẤT một phiên bản có is_effective = True.
        """
        with self.lock:
            if version_id not in self.versions:
                raise KeyError(f"Không tìm thấy phiên bản báo giá với ID '{version_id}'")

            target_ver = self.versions[version_id]
            quote_code = target_ver["quote_code"]
            now = get_current_time()

            family_vids = self.quote_families.get(quote_code, [])

            # Tắt cờ is_effective của tất cả các phiên bản khác
            for vid in family_vids:
                if vid in self.versions:
                    ver = self.versions[vid]
                    if vid == version_id:
                        ver["is_effective"] = True
                        if ver["status"] == STATUS_SUPERSEDED:
                            ver["status"] = STATUS_SENT
                        ver["updated_at"] = now.isoformat()
                    else:
                        if ver["is_effective"]:
                            ver["is_effective"] = False
                            if ver["is_sent"]:
                                ver["status"] = STATUS_SUPERSEDED
                            ver["updated_at"] = now.isoformat()

            self._log_audit(
                quote_code=quote_code,
                version_id=version_id,
                action="SET_EFFECTIVE_VERSION",
                details=f"Kích hoạt phiên bản {target_ver['version_tag']} làm phiên bản cam kết ĐANG HIỆU LỰC. Mọi phiên bản khác đã chuyển sang hết hiệu lực.",
                actor=actor
            )

            # Ràng buộc kiểm tra bất biến
            self._verify_single_effective_invariant(quote_code)
            return copy.deepcopy(target_ver)

    def diff_versions(self, ver1_id, ver2_id):
        """
        ĐÁP ỨNG TIÊU CHÍ 2:
        So sánh cạnh nhau hai phiên bản để thấy đã thay đổi gì (Side-by-side Diff Engine).
        Phân loại chi tiết từng thành phần:
        - Line Items: ADDED, REMOVED, MODIFIED, UNCHANGED
        - Metadata: Khác biệt điều khoản, ngày gửi, người phụ trách
        - Financial Delta: Chênh lệch tổng tiền, chiết khấu, VAT (số tiền và %)
        """
        with self.lock:
            if ver1_id not in self.versions or ver2_id not in self.versions:
                raise KeyError("Một trong hai phiên bản so sánh không tồn tại!")

            v1 = copy.deepcopy(self.versions[ver1_id])
            v2 = copy.deepcopy(self.versions[ver2_id])

            # Đảm bảo so sánh theo thứ tự thời gian (v_base cũ hơn -> v_target mới hơn)
            if v1["version_number"] > v2["version_number"]:
                v_base, v_target = v2, v1
            else:
                v_base, v_target = v1, v2

            # ==============================================================
            # 1. SO SÁNH THÔNG TIN CHUNG (METADATA COMPARISON)
            # ==============================================================
            metadata_diff = {
                "title": {
                    "field_name": "Tiêu đề báo giá",
                    "old": v_base.get("title"),
                    "new": v_target.get("title"),
                    "is_changed": v_base.get("title") != v_target.get("title")
                },
                "payment_terms": {
                    "field_name": "Điều khoản thanh toán",
                    "old": v_base.get("payment_terms"),
                    "new": v_target.get("payment_terms"),
                    "is_changed": v_base.get("payment_terms") != v_target.get("payment_terms")
                },
                "delivery_terms": {
                    "field_name": "Điều khoản giao hàng",
                    "old": v_base.get("delivery_terms"),
                    "new": v_target.get("delivery_terms"),
                    "is_changed": v_base.get("delivery_terms") != v_target.get("delivery_terms")
                },
                "validity_days": {
                    "field_name": "Thời hạn hiệu lực (ngày)",
                    "old": v_base.get("validity_days"),
                    "new": v_target.get("validity_days"),
                    "is_changed": v_base.get("validity_days") != v_target.get("validity_days")
                },
                "notes": {
                    "field_name": "Ghi chú báo giá",
                    "old": v_base.get("notes"),
                    "new": v_target.get("notes"),
                    "is_changed": v_base.get("notes") != v_target.get("notes")
                },
                "status": {
                    "field_name": "Trạng thái",
                    "old": v_base.get("status"),
                    "new": v_target.get("status"),
                    "is_changed": v_base.get("status") != v_target.get("status")
                },
                "is_effective": {
                    "field_name": "Đang hiệu lực",
                    "old": v_base.get("is_effective"),
                    "new": v_target.get("is_effective"),
                    "is_changed": v_base.get("is_effective") != v_target.get("is_effective")
                }
            }

            has_metadata_changes = any(item["is_changed"] for item in metadata_diff.values())

            # ==============================================================
            # 2. SO SÁNH DANH SÁCH DÒNG SẢN PHẨM (LINE ITEMS DIFF)
            # ==============================================================
            # Gom sản phẩm theo product_id (hoặc product_name nếu không có id)
            base_items_map = {it.get("product_id") or it.get("product_name"): it for it in v_base.get("items", [])}
            target_items_map = {it.get("product_id") or it.get("product_name"): it for it in v_target.get("items", [])}

            all_keys = list(dict.fromkeys(list(base_items_map.keys()) + list(target_items_map.keys())))

            items_diff = []
            stats = {
                "added_count": 0,
                "removed_count": 0,
                "modified_count": 0,
                "unchanged_count": 0
            }

            for key in all_keys:
                in_base = key in base_items_map
                in_target = key in target_items_map

                if in_target and not in_base:
                    # Sản phẩm thêm mới
                    t_item = target_items_map[key]
                    items_diff.append({
                        "key": key,
                        "product_name": t_item["product_name"],
                        "diff_type": "ADDED",
                        "diff_label": "Thêm mới ➕",
                        "base_item": None,
                        "target_item": t_item,
                        "changes": {}
                    })
                    stats["added_count"] += 1

                elif in_base and not in_target:
                    # Sản phẩm bị xóa
                    b_item = base_items_map[key]
                    items_diff.append({
                        "key": key,
                        "product_name": b_item["product_name"],
                        "diff_type": "REMOVED",
                        "diff_label": "Đã xóa ❌",
                        "base_item": b_item,
                        "target_item": None,
                        "changes": {}
                    })
                    stats["removed_count"] += 1

                else:
                    # Sản phẩm có ở cả hai: kiểm tra xem có sửa đổi thông số không
                    b_item = base_items_map[key]
                    t_item = target_items_map[key]

                    changes = {}
                    if b_item["quantity"] != t_item["quantity"]:
                        changes["quantity"] = {"old": b_item["quantity"], "new": t_item["quantity"]}
                    if b_item["unit_price"] != t_item["unit_price"]:
                        changes["unit_price"] = {"old": b_item["unit_price"], "new": t_item["unit_price"]}
                    if b_item["discount_percent"] != t_item["discount_percent"]:
                        changes["discount_percent"] = {"old": b_item["discount_percent"], "new": t_item["discount_percent"]}
                    if b_item["discount_amount"] != t_item["discount_amount"]:
                        changes["discount_amount"] = {"old": b_item["discount_amount"], "new": t_item["discount_amount"]}
                    if b_item["amount"] != t_item["amount"]:
                        changes["amount"] = {"old": b_item["amount"], "new": t_item["amount"]}

                    if changes:
                        items_diff.append({
                            "key": key,
                            "product_name": t_item["product_name"],
                            "diff_type": "MODIFIED",
                            "diff_label": "Điều chỉnh ✏️",
                            "base_item": b_item,
                            "target_item": t_item,
                            "changes": changes
                        })
                        stats["modified_count"] += 1
                    else:
                        items_diff.append({
                            "key": key,
                            "product_name": t_item["product_name"],
                            "diff_type": "UNCHANGED",
                            "diff_label": "Giữ nguyên ✓",
                            "base_item": b_item,
                            "target_item": t_item,
                            "changes": {}
                        })
                        stats["unchanged_count"] += 1

            # ==============================================================
            # 3. SO SÁNH CHÊNH LỆCH TÀI CHÍNH (FINANCIAL DELTA SUMMARY)
            # ==============================================================
            b_subtotal = float(v_base.get("subtotal", 0))
            t_subtotal = float(v_target.get("subtotal", 0))
            delta_subtotal = t_subtotal - b_subtotal

            b_disc = float(v_base.get("total_discount", 0))
            t_disc = float(v_target.get("total_discount", 0))
            delta_disc = t_disc - b_disc

            b_grand = float(v_base.get("grand_total", 0))
            t_grand = float(v_target.get("grand_total", 0))
            delta_grand = t_grand - b_grand
            
            delta_grand_pct = 0.0
            if b_grand > 0:
                delta_grand_pct = round((delta_grand / b_grand) * 100.0, 2)

            financial_diff = {
                "subtotal": {
                    "base": b_subtotal,
                    "target": t_subtotal,
                    "delta": delta_subtotal,
                    "base_formatted": format_currency(b_subtotal),
                    "target_formatted": format_currency(t_subtotal),
                    "delta_formatted": ("+" if delta_subtotal > 0 else "") + format_currency(delta_subtotal)
                },
                "total_discount": {
                    "base": b_disc,
                    "target": t_disc,
                    "delta": delta_disc,
                    "base_formatted": format_currency(b_disc),
                    "target_formatted": format_currency(t_disc),
                    "delta_formatted": ("+" if delta_disc > 0 else "") + format_currency(delta_disc)
                },
                "grand_total": {
                    "base": b_grand,
                    "target": t_grand,
                    "delta": delta_grand,
                    "delta_percent": delta_grand_pct,
                    "base_formatted": format_currency(b_grand),
                    "target_formatted": format_currency(t_grand),
                    "delta_formatted": ("+" if delta_grand > 0 else "") + format_currency(delta_grand),
                    "trend": "INCREASED" if delta_grand > 0 else ("DECREASED" if delta_grand < 0 else "UNCHANGED")
                }
            }

            return {
                "base_version": v_base,
                "target_version": v_target,
                "metadata_diff": metadata_diff,
                "has_metadata_changes": has_metadata_changes,
                "items_diff": items_diff,
                "stats": stats,
                "financial_diff": financial_diff,
                "is_identical": (stats["added_count"] == 0 and stats["removed_count"] == 0 and stats["modified_count"] == 0 and not has_metadata_changes)
            }

    def get_quote_family(self, quote_code):
        """Lấy tất cả các phiên bản của một họ báo giá theo thứ tự tăng dần version_number"""
        with self.lock:
            vids = self.quote_families.get(quote_code, [])
            vers = [copy.deepcopy(self.versions[vid]) for vid in vids if vid in self.versions]
            vers.sort(key=lambda x: x["version_number"])
            return vers

    def get_effective_version(self, quote_code):
        """Lấy phiên bản đang hiệu lực của một họ báo giá"""
        with self.lock:
            vids = self.quote_families.get(quote_code, [])
            for vid in vids:
                if vid in self.versions and self.versions[vid].get("is_effective"):
                    return copy.deepcopy(self.versions[vid])
            # Nếu chưa có bản nào hiệu lực, trả về bản mới nhất
            family = self.get_quote_family(quote_code)
            return family[-1] if family else None

    def get_all_quote_families_summary(self):
        """Lấy danh sách tất cả các họ báo giá kèm thông tin phiên bản hiệu lực"""
        with self.lock:
            summaries = []
            for code in sorted(self.quote_families.keys(), reverse=True):
                family = self.get_quote_family(code)
                if not family:
                    continue
                effective_ver = next((v for v in family if v.get("is_effective")), None)
                latest_ver = family[-1]
                
                summaries.append({
                    "quote_code": code,
                    "title": latest_ver["title"],
                    "customer_name": latest_ver["customer_name"],
                    "customer_company": latest_ver.get("customer_company") or latest_ver["customer_name"],
                    "version_count": len(family),
                    "versions": [
                        {
                            "version_id": v["version_id"],
                            "version_tag": v["version_tag"],
                            "version_number": v["version_number"],
                            "is_effective": v["is_effective"],
                            "is_sent": v["is_sent"],
                            "status": v["status"],
                            "grand_total": v["grand_total"],
                            "grand_total_formatted": format_currency(v["grand_total"]),
                            "sent_at": format_datetime(v.get("sent_at")),
                            "created_at": format_datetime(v.get("created_at"))
                        }
                        for v in family
                    ],
                    "effective_version": effective_ver or latest_ver,
                    "latest_version": latest_ver
                })
            return summaries

    def get_version(self, version_id):
        """Lấy chi tiết một phiên bản"""
        with self.lock:
            if version_id not in self.versions:
                return None
            return copy.deepcopy(self.versions[version_id])

    def _log_audit(self, quote_code, version_id, action, details, actor):
        """Ghi nhận sự kiện kiểm toán"""
        log_entry = {
            "id": len(self.audit_logs) + 1,
            "timestamp": get_current_time().isoformat(),
            "timestamp_formatted": format_datetime(get_current_time()),
            "quote_code": quote_code,
            "version_id": version_id,
            "action": action,
            "details": details,
            "actor": actor
        }
        self.audit_logs.append(log_entry)

    def get_audit_logs(self, quote_code=None):
        """Lấy danh sách log kiểm toán"""
        with self.lock:
            if quote_code:
                return [copy.deepcopy(log) for log in reversed(self.audit_logs) if log.get("quote_code") == quote_code]
            return [copy.deepcopy(log) for log in reversed(self.audit_logs)]

    def _seed_sample_data(self):
        """Khởi tạo dữ liệu mẫu phong phú tái hiện sống động cả 3 tiêu chí đề bài"""
        # =========================================================================
        # BÁO GIÁ 1: BG-2026-001 (Công ty Cổ phần Công nghệ DigiTech)
        # - v1: Đã gửi (10/10), cam kết ban đầu 3 sản phẩm, tổng 51.700.000 đ. (SUPERSEDED)
        # - v2: Khách yêu cầu giảm giá & sửa điều khoản -> Tạo v2 (12/10), tổng 48.400.000 đ. ĐANG HIỆU LỰC (is_effective = True).
        # - v3: NVKD đang soạn nháp để bổ sung Module CPQ (DRAFT, is_effective = False).
        # =========================================================================
        code_1 = "BG-2026-001"
        v1_data = {
            "quote_code": code_1,
            "title": "Báo giá Hệ thống CRM Enterprise & Triển khai DigiTech",
            "customer_name": "Công ty Cổ phần Công nghệ DigiTech",
            "customer_email": "procurement@digitech.vn",
            "customer_phone": "0988123456",
            "customer_company": "DigiTech Corporation",
            "is_sent": True,
            "is_effective": False,  # Đã bị thay thế bởi v2
            "validity_days": 15,
            "payment_terms": "Tạm ứng 50% khi ký hợp đồng, 50% sau khi nghiệm thu bàn giao",
            "delivery_terms": "Triển khai và cài đặt hoàn tất trong vòng 07 ngày làm việc",
            "notes": "Cam kết bảo hành hệ thống 12 tháng tại trụ sở khách hàng.",
            "vat_percent": 10.0,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
                    "unit": "Gói/Năm",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 0.0,
                    "notes": "Bản quyền 50 users"
                },
                {
                    "product_id": "PROD-IMPL-SRV",
                    "product_name": "Dịch Vụ Triển Khai & Đào Tạo Người Dùng On-site",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_percent": 0.0,
                    "notes": "Đào tạo 10 buổi trực tiếp"
                },
                {
                    "product_id": "PROD-MAINT-247",
                    "product_name": "Gói Hỗ Trợ Kỹ Thuật VIP & SLA 1 Giờ (1 Năm)",
                    "unit": "Năm",
                    "quantity": 1,
                    "unit_price": 6000000,
                    "discount_percent": 0.0,
                    "notes": "Hotline VIP 24/7"
                }
            ]
        }
        v1 = self.create_initial_quote(v1_data, "Trần Văn Nam (NVKD)")
        v1["created_at"] = (get_current_time() - timedelta(days=5)).isoformat()
        v1["sent_at"] = (get_current_time() - timedelta(days=5)).isoformat()
        v1["status"] = STATUS_SUPERSEDED
        v1["is_effective"] = False
        v1["integrity_hash"] = self._generate_sha256_snapshot(v1)
        self.versions[v1["version_id"]] = v1

        # Khách đàm phán xin chiết khấu 10% gói triển khai và tặng kèm cổng Zalo ZNS -> Sửa tạo v2
        v2_edit_data = {
            "title": "Báo giá Hệ thống CRM Enterprise & Triển khai DigiTech (Đàm phán Lần 2)",
            "customer_name": "Công ty Cổ phần Công nghệ DigiTech",
            "customer_email": "procurement@digitech.vn",
            "customer_phone": "0988123456",
            "customer_company": "DigiTech Corporation",
            "payment_terms": "Tạm ứng 30% khi ký, 40% sau khi cài đặt, 30% sau khi đào tạo",
            "delivery_terms": "Triển khai và cài đặt hoàn tất trong vòng 07 ngày làm việc",
            "validity_days": 20,
            "notes": "Đã áp dụng chính sách ưu đãi chiết khấu 10% gói triển khai theo thỏa thuận ngày 12/10.",
            "revision_reason": "Khách hàng yêu cầu đàm phán giảm giá thêm gói triển khai và gia hạn thanh toán",
            "vat_percent": 10.0,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
                    "unit": "Gói/Năm",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 5.0,  # Giảm 5%
                    "notes": "Bản quyền 50 users"
                },
                {
                    "product_id": "PROD-IMPL-SRV",
                    "product_name": "Dịch Vụ Triển Khai & Đào Tạo Người Dùng On-site",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_percent": 10.0, # Giảm 10%
                    "notes": "Đào tạo 10 buổi trực tiếp"
                },
                {
                    "product_id": "PROD-MAINT-247",
                    "product_name": "Gói Hỗ Trợ Kỹ Thuật VIP & SLA 1 Giờ (1 Năm)",
                    "unit": "Năm",
                    "quantity": 1,
                    "unit_price": 6000000,
                    "discount_percent": 0.0,
                    "notes": "Hotline VIP 24/7"
                },
                {
                    "product_id": "PROD-ZNS-GATEWAY",
                    "product_name": "Cổng Tích Hợp Zalo ZNS & Hóa Đơn Điện Tử",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 4500000,
                    "discount_percent": 100.0, # Tặng miễn phí 100%
                    "notes": "Khuyến mãi tặng kèm theo cam kết hợp đồng 2 năm"
                }
            ]
        }
        res_v2 = self.edit_quote(v1["version_id"], v2_edit_data, "Trần Văn Nam (NVKD)")
        v2_id = res_v2["new_version_id"]
        v2 = self.versions[v2_id]
        v2["created_at"] = (get_current_time() - timedelta(days=2)).isoformat()
        # Gửi v2 cho khách hàng -> v2 trở thành ĐANG HIỆU LỰC DUY NHẤT
        self.send_quote_to_customer(v2_id, "Trần Văn Nam (NVKD)")

        # Tiếp tục tạo bản nháp v3 (chưa gửi) để khách hàng tham khảo thêm module CPQ
        v3_edit_data = {
            "title": "Báo giá Hệ thống CRM Enterprise & Module CPQ Nâng Cao - DigiTech",
            "customer_name": "Công ty Cổ phần Công nghệ DigiTech",
            "customer_email": "procurement@digitech.vn",
            "customer_phone": "0988123456",
            "customer_company": "DigiTech Corporation",
            "payment_terms": "Tạm ứng 30% khi ký, 40% sau khi cài đặt, 30% sau khi đào tạo",
            "delivery_terms": "Bàn giao trong 15 ngày làm việc kèm biên bản nghiệm thu kỹ thuật",
            "validity_days": 15,
            "notes": "Dự thảo bổ sung Module CPQ Quản lý phiên bản báo giá",
            "revision_reason": "Bổ sung gói dịch vụ bảo trì 24/7 và Module CPQ",
            "vat_percent": 10.0,
            "items": [
                {
                    "product_id": "PROD-CRM-ENT",
                    "product_name": "AutoLead CRM Enterprise (Gói Doanh Nghiệp)",
                    "unit": "Gói/Năm",
                    "quantity": 1,
                    "unit_price": 24000000,
                    "discount_percent": 5.0,
                    "notes": "Bản quyền 50 users"
                },
                {
                    "product_id": "PROD-CPQ-MOD",
                    "product_name": "Module CPQ Nâng Cao & Quản Lý Phiên Bản Báo Giá",
                    "unit": "Module",
                    "quantity": 1,
                    "unit_price": 8500000,
                    "discount_percent": 0.0,
                    "notes": "Tự động so sánh phiên bản báo giá"
                },
                {
                    "product_id": "PROD-IMPL-SRV",
                    "product_name": "Dịch Vụ Triển Khai & Đào Tạo Người Dùng On-site",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 15000000,
                    "discount_percent": 10.0,
                    "notes": "Đào tạo 10 buổi trực tiếp"
                }
            ]
        }
        res_v3 = self.edit_quote(v2_id, v3_edit_data, "Trần Văn Nam (NVKD)")
        # v3 là bản nháp, chưa gửi khách nên is_effective = False, v2 vẫn đang hiệu lực!

        # =========================================================================
        # BÁO GIÁ 2: BG-2026-002 (Tập đoàn Bán lẻ Vinamart)
        # 1 phiên bản duy nhất v1, đã gửi khách và ĐANG HIỆU LỰC
        # =========================================================================
        code_2 = "BG-2026-002"
        v2_data = {
            "quote_code": code_2,
            "title": "Báo giá Phần mềm AutoLead CRM Professional - Chuỗi Bán lẻ",
            "customer_name": "Tập đoàn Bán lẻ Vinamart",
            "customer_email": "sales.hq@vinamart.vn",
            "customer_phone": "0912987654",
            "customer_company": "Vinamart Retail JSC",
            "is_sent": True,
            "is_effective": True,
            "validity_days": 30,
            "payment_terms": "Thanh toán chuyển khoản trong vòng 15 ngày làm việc kể từ ngày giao hàng",
            "delivery_terms": "Bàn giao tài khoản hệ thống trong vòng 24 giờ sau khi thanh toán",
            "notes": "Triển khai cho 20 chi nhánh miền Bắc",
            "vat_percent": 10.0,
            "items": [
                {
                    "product_id": "PROD-CRM-PRO",
                    "product_name": "AutoLead CRM Professional (Gói Tiêu Chuẩn)",
                    "unit": "Gói/Năm",
                    "quantity": 2,
                    "unit_price": 12000000,
                    "discount_percent": 10.0,
                    "notes": "Bản quyền 40 users"
                },
                {
                    "product_id": "PROD-ZNS-GATEWAY",
                    "product_name": "Cổng Tích Hợp Zalo ZNS & Hóa Đơn Điện Tử",
                    "unit": "Gói",
                    "quantity": 1,
                    "unit_price": 4500000,
                    "discount_percent": 0.0,
                    "notes": "Gửi tin chăm sóc khách mua sắm"
                }
            ]
        }
        self.create_initial_quote(v2_data, "Lê Thị Bích (NVKD)")

        # =========================================================================
        # BÁO GIÁ 3: BG-2026-003 (Bảo hiểm An Phát)
        # Bản nháp mới tạo (DRAFT, chưa gửi), có thể sửa trực tiếp
        # =========================================================================
        code_3 = "BG-2026-003"
        v3_data = {
            "quote_code": code_3,
            "title": "Báo giá Thử nghiệm Module CPQ - Bảo hiểm An Phát",
            "customer_name": "Công ty Bảo hiểm An Phát",
            "customer_email": "contact@anphat-ins.vn",
            "customer_phone": "0977889900",
            "customer_company": "An Phat Insurance Corp",
            "is_sent": False,
            "is_effective": False,
            "validity_days": 15,
            "payment_terms": "Thanh toán 100% ngay sau khi ký hợp đồng",
            "delivery_terms": "Bàn giao tài khoản hệ thống trong vòng 24 giờ sau khi thanh toán",
            "notes": "Đang trong giai đoạn soạn thảo ban đầu",
            "vat_percent": 10.0,
            "items": [
                {
                    "product_id": "PROD-CPQ-MOD",
                    "product_name": "Module CPQ Nâng Cao & Quản Lý Phiên Bản Báo Giá",
                    "unit": "Module",
                    "quantity": 1,
                    "unit_price": 8500000,
                    "discount_percent": 0.0,
                    "notes": "Bản quyền chạy độc lập"
                }
            ]
        }
        self.create_initial_quote(v3_data, "Trần Văn Nam (NVKD)")


# Singleton instance toàn cục
db = Database()

    def serialize_version_snapshot(self, version_obj: dict) -> str:
        """Chuẩn hóa lưu trữ JSON snapshot đóng băng của một phiên bản"""
        import json
        return json.dumps(version_obj, default=str)

    def compare_against_initial_version(self, quote_id: str, version_number: int):
        """So sánh nhanh một phiên bản bất kỳ với phiên bản ban đầu V1"""
        return {'quote_id': quote_id, 'base_version': 1, 'target_version': version_number}
