"""
Cơ sở dữ liệu Thread-Safe & Động Cơ Tính Toán Báo Cáo Hiệu Quả Marketing
Ticket: SCRUM-30 / SCRUM-99

Đáp ứng 3 Tiêu chí chấp nhận:
1. Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn và từng chiến dịch.
2. Lọc theo khoảng thời gian linh hoạt (Presets & Tùy chọn ngày).
3. Hỗ trợ dữ liệu đầy đủ sẵn sàng xuất Excel chuẩn.
"""

import threading
import copy
from datetime import datetime, timedelta, date

from config import (
    SOURCES,
    SOURCE_ICONS,
    SOURCE_COLORS,
    CAMPAIGNS_DEF,
    ROLE_MARKETING,
    ROLE_SALES_REP,
    ROLE_TEAM_LEAD,
    ROLE_DIRECTOR,
    STATUS_NEW,
    STATUS_ACCEPTED,
    STATUS_OPPORTUNITY,
    STATUS_WON,
    STATUS_REJECTED,
    STATUS_LOST
)


def format_currency(amount):
    """Format tiền tệ VND đẹp mắt"""
    try:
        val = float(amount or 0)
        return f"{val:,.0f} đ".replace(",", ".")
    except Exception:
        return f"{amount} đ"


def format_percent(rate):
    """Format tỷ lệ % với 1 chữ số thập phân"""
    try:
        return f"{float(rate):.1f}%"
    except Exception:
        return "0.0%"


def format_datetime(dt):
    """Format datetime sang định dạng tiếng Việt trực quan"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%H:%M:%S %d/%m/%Y")


def format_date(dt):
    """Format ngày dd/mm/yyyy"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%d/%m/%Y")


class Database:
    def __init__(self):
        self.lock = threading.RLock()
        self.users = {}
        self.campaigns = {}
        self.leads = []
        self._lead_counter = 1000

        self.reset_demo_data()

    def reset_demo_data(self):
        """Khởi tạo dữ liệu mẫu mô phỏng dữ liệu Marketing & Bán hàng B2B thực tế"""
        with self.lock:
            # 1. Danh sách người dùng
            self.users = {
                "usr-mkt-01": {
                    "id": "usr-mkt-01",
                    "name": "Trần Phương Linh",
                    "email": "linh.tran@autolead.vn",
                    "role": ROLE_MARKETING,
                    "role_name": "Chuyên viên Marketing",
                    "avatar": "👩‍💻"
                },
                "usr-mkt-02": {
                    "id": "usr-mkt-02",
                    "name": "Vũ Hoàng Minh",
                    "email": "minh.vu@autolead.vn",
                    "role": ROLE_MARKETING,
                    "role_name": "Trưởng phòng Digital Marketing",
                    "avatar": "👨‍💻"
                },
                "usr-sales-01": {
                    "id": "usr-sales-01",
                    "name": "Nguyễn Văn Tuấn",
                    "email": "tuan.nguyen@autolead.vn",
                    "role": ROLE_SALES_REP,
                    "role_name": "Nhân viên kinh doanh",
                    "avatar": "👨‍💼"
                },
                "usr-dir-01": {
                    "id": "usr-dir-01",
                    "name": "Phạm Đức Thắng",
                    "email": "thang.pham@autolead.vn",
                    "role": ROLE_DIRECTOR,
                    "role_name": "Giám đốc Kinh doanh & Tiếp thị",
                    "avatar": "👔"
                }
            }

            # 2. Danh sách chiến dịch
            self.campaigns = {}
            for camp in CAMPAIGNS_DEF:
                self.campaigns[camp["id"]] = copy.deepcopy(camp)

            # 3. Dữ liệu Lead phong phú với thời gian rải đều trong các mốc (Hôm nay, tuần này, tháng này, quý này)
            now = datetime.now()
            self.leads = []

            # Danh sách hạt giống lead thực tế
            raw_leads = [
                # GOOGLE ADS (Nguồn có chuyển đổi cao và doanh thu rất tốt -> Khuyên dồn ngân sách)
                {"corp": "Công ty CP Công nghệ AI NextGen", "contact": "Bùi Văn An", "phone": "0912 111 222", "camp": "CAMP-01", "days_ago": 2, "status": STATUS_WON, "opp_val": 120000000, "rev": 120000000},
                {"corp": "Tập đoàn Xây dựng & Địa ốc Phúc Thịnh", "contact": "Lê Thị Bích", "phone": "0988 222 333", "camp": "CAMP-01", "days_ago": 5, "status": STATUS_WON, "opp_val": 95000000, "rev": 95000000},
                {"corp": "Công ty Dược phẩm BioPharm Hà Nội", "contact": "Ngô Hoàng Cường", "phone": "0903 333 444", "camp": "CAMP-01", "days_ago": 7, "status": STATUS_OPPORTUNITY, "opp_val": 80000000, "rev": 0},
                {"corp": "Chuỗi Bệnh viện Đa khoa Quốc tế Tâm Anh", "contact": "Đặng Thu Dung", "phone": "0977 444 555", "camp": "CAMP-01", "days_ago": 12, "status": STATUS_ACCEPTED, "opp_val": 60000000, "rev": 0},
                {"corp": "Công ty Vận tải & Logistics Biển Đông", "contact": "Phạm Hữu Đạt", "phone": "0934 555 666", "camp": "CAMP-01", "days_ago": 16, "status": STATUS_WON, "opp_val": 150000000, "rev": 150000000},
                {"corp": "Tổng Công ty Bảo hiểm Toàn Cầu", "contact": "Vũ Đình Giang", "phone": "0918 666 777", "camp": "CAMP-01", "days_ago": 20, "status": STATUS_OPPORTUNITY, "opp_val": 70000000, "rev": 0},
                {"corp": "Công ty Nội thất Xuất khẩu Tân Á", "contact": "Hoàng Minh Hải", "phone": "0909 777 888", "camp": "CAMP-01", "days_ago": 25, "status": STATUS_ACCEPTED, "opp_val": 45000000, "rev": 0},
                {"corp": "Công ty Năng lượng Xanh EcoPower", "contact": "Trịnh Thị Khang", "phone": "0982 888 999", "camp": "CAMP-01", "days_ago": 35, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Nhà máy Cơ khí Chính xác Hòa Phát", "contact": "Lý Quang Liêm", "phone": "0944 999 000", "camp": "CAMP-01", "days_ago": 40, "status": STATUS_WON, "opp_val": 180000000, "rev": 180000000},
                {"corp": "Tập đoàn Giáo dục & Đào tạo E-Edu", "contact": "Chu Đình Mạnh", "phone": "0932 123 456", "camp": "CAMP-01", "days_ago": 1, "status": STATUS_NEW, "opp_val": 50000000, "rev": 0},

                # FACEBOOK ADS (Số lượng lead lớn, nhưng tỷ lệ từ chối cao, ra ít cơ hội -> Cần tối ưu lọc lead)
                {"corp": "Cửa hàng Thời trang ChicStyle", "contact": "Mai Phương Nga", "phone": "0966 234 567", "camp": "CAMP-02", "days_ago": 1, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Nhà hàng Lẩu Nướng KingBBQ Hoàng Cầu", "contact": "Đỗ Thành Nam", "phone": "0915 345 678", "camp": "CAMP-02", "days_ago": 3, "status": STATUS_ACCEPTED, "opp_val": 30000000, "rev": 0},
                {"corp": "Công ty TNHH Tư vấn Du học Quốc Tế", "contact": "Phan Hoài Oanh", "phone": "0908 456 789", "camp": "CAMP-02", "days_ago": 4, "status": STATUS_OPPORTUNITY, "opp_val": 45000000, "rev": 0},
                {"corp": "Spa & Thẩm mỹ viện Lavender", "contact": "Bùi Diễm Phúc", "phone": "0971 567 890", "camp": "CAMP-02", "days_ago": 6, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Hộ kinh doanh Điện Máy Anh Tuấn", "contact": "Dương Văn Quân", "phone": "0938 678 901", "camp": "CAMP-02", "days_ago": 8, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Trung tâm Tiếng Anh Rainbow Kids", "contact": "Lương Ngọc Sơn", "phone": "0989 789 012", "camp": "CAMP-02", "days_ago": 14, "status": STATUS_WON, "opp_val": 55000000, "rev": 55000000},
                {"corp": "Gara Ô Tô AutoPro Thanh Xuân", "contact": "Hà Văn Toàn", "phone": "0922 890 123", "camp": "CAMP-02", "days_ago": 18, "status": STATUS_LOST, "opp_val": 40000000, "rev": 0},
                {"corp": "Studio Áo Cưới Mơ Ước", "contact": "Trương Cẩm Uyên", "phone": "0904 901 234", "camp": "CAMP-02", "days_ago": 22, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Nha Khoa Thẩm Mỹ Quốc Tế Smile", "contact": "Thái Đức Vượng", "phone": "0949 012 345", "camp": "CAMP-02", "days_ago": 28, "status": STATUS_OPPORTUNITY, "opp_val": 50000000, "rev": 0},
                {"corp": "Đại lý Phân phối Sữa Mẹ & Bé", "contact": "Đoàn Mỹ Xuân", "phone": "0963 123 789", "camp": "CAMP-02", "days_ago": 0, "status": STATUS_NEW, "opp_val": 25000000, "rev": 0},

                # SỰ KIỆN TECH EXPO (Chi phí cao nhưng chốt được hợp đồng khủng B2B -> Ra doanh thu rất lớn)
                {"corp": "Tập đoàn Bán lẻ VinCommerce", "contact": "Nguyễn Hoàng Long", "phone": "0918 888 999", "camp": "CAMP-03", "days_ago": 15, "status": STATUS_WON, "opp_val": 280000000, "rev": 280000000},
                {"corp": "Công ty May mặc Xuất khẩu Thăng Long", "contact": "Trần Thu Trang", "phone": "0905 111 333", "camp": "CAMP-03", "days_ago": 16, "status": STATUS_WON, "opp_val": 160000000, "rev": 160000000},
                {"corp": "Ngân hàng Thương mại Cổ phần Á Châu", "contact": "Phạm Quốc Tuấn", "phone": "0983 222 444", "camp": "CAMP-03", "days_ago": 18, "status": STATUS_OPPORTUNITY, "opp_val": 220000000, "rev": 0},
                {"corp": "Chuỗi Khách sạn Mường Thanh Heritage", "contact": "Lê Văn Hưng", "phone": "0936 333 555", "camp": "CAMP-03", "days_ago": 21, "status": STATUS_ACCEPTED, "opp_val": 110000000, "rev": 0},
                {"corp": "Hãng Phân bón & Hóa chất Miền Trung", "contact": "Vũ Đình Khoa", "phone": "0972 444 666", "camp": "CAMP-03", "days_ago": 24, "status": STATUS_WON, "opp_val": 190000000, "rev": 190000000},

                # ĐỐI TÁC GIỚI THIỆU (REFERRAL - Chi phí thấp, tỷ lệ nhận và chốt cực cao -> ROI khủng)
                {"corp": "Công ty TNHH Phần mềm FAST Solution", "contact": "Đỗ Bích Ngọc", "phone": "0919 555 777", "camp": "CAMP-05", "days_ago": 3, "status": STATUS_WON, "opp_val": 90000000, "rev": 90000000},
                {"corp": "Công ty Kế toán & Kiểm toán Việt Á", "contact": "Trần Quốc Bảo", "phone": "0981 666 888", "camp": "CAMP-05", "days_ago": 8, "status": STATUS_WON, "opp_val": 75000000, "rev": 75000000},
                {"corp": "Tập đoàn Vận tải Hàng hải Vinalines", "contact": "Nguyễn Thanh Sơn", "phone": "0902 777 999", "camp": "CAMP-05", "days_ago": 11, "status": STATUS_WON, "opp_val": 130000000, "rev": 130000000},
                {"corp": "Công ty Nông sản Sạch Đà Lạt Farm", "contact": "Lê Thùy Linh", "phone": "0974 888 000", "camp": "CAMP-05", "days_ago": 19, "status": STATUS_OPPORTUNITY, "opp_val": 65000000, "rev": 0},
                {"corp": "Công ty Chứng khoán Rồng Việt", "contact": "Võ Hoàng Nam", "phone": "0939 999 111", "camp": "CAMP-05", "days_ago": 27, "status": STATUS_WON, "opp_val": 115000000, "rev": 115000000},

                # WEBSITE ORGANIC / SEO (Chi phí duy trì thấp, lead chất lượng đều đặn)
                {"corp": "Công ty Truyền thông đa phương tiện Apex", "contact": "Hồ Thị Mai", "phone": "0914 123 321", "camp": "CAMP-04", "days_ago": 2, "status": STATUS_ACCEPTED, "opp_val": 40000000, "rev": 0},
                {"corp": "Viện Nghiên cứu Vật liệu Tiên tiến", "contact": "Đinh Công Thành", "phone": "0987 234 432", "camp": "CAMP-04", "days_ago": 9, "status": STATUS_WON, "opp_val": 85000000, "rev": 85000000},
                {"corp": "Trường Quốc tế Song ngữ Wellspring", "contact": "Tô Ngọc Ánh", "phone": "0906 345 543", "camp": "CAMP-04", "days_ago": 17, "status": STATUS_OPPORTUNITY, "opp_val": 70000000, "rev": 0},
                {"corp": "Công ty TNHH Nhựa Composite Tân Tiến", "contact": "Cao Bá Quát", "phone": "0978 456 654", "camp": "CAMP-04", "days_ago": 30, "status": STATUS_WON, "opp_val": 65000000, "rev": 65000000},

                # EMAIL MARKETING (Chi phí thấp, nuôi dưỡng túc tắc)
                {"corp": "Công ty Cơ điện Lạnh SEAREFICO", "contact": "Bùi Tấn Tài", "phone": "0916 567 765", "camp": "CAMP-06", "days_ago": 6, "status": STATUS_ACCEPTED, "opp_val": 50000000, "rev": 0},
                {"corp": "Công ty Thức ăn Chăn nuôi C.P Group", "contact": "Vũ Văn Thanh", "phone": "0984 678 876", "camp": "CAMP-06", "days_ago": 13, "status": STATUS_OPPORTUNITY, "opp_val": 95000000, "rev": 0},
                {"corp": "Công ty In ấn & Bao bì Hải Nam", "contact": "Trịnh Xuân Trường", "phone": "0901 789 987", "camp": "CAMP-06", "days_ago": 23, "status": STATUS_LOST, "opp_val": 35000000, "rev": 0},

                # TIKTOK ADS (Nhiều lead cá nhân nhỏ lẻ, ít ra doanh thu B2B -> Khuyên cắt giảm ngân sách)
                {"corp": "Shop Phụ Kiện Điện Thoại 99k", "contact": "Nguyễn Tiến Linh", "phone": "0975 890 098", "camp": "CAMP-07", "days_ago": 1, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Bán Hàng Online Tạp Hóa Xanh", "contact": "Đoàn Văn Hậu", "phone": "0937 901 109", "camp": "CAMP-07", "days_ago": 4, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Cửa Hàng Trà Sữa Đô Đô", "contact": "Quế Ngọc Hải", "phone": "0911 012 210", "camp": "CAMP-07", "days_ago": 8, "status": STATUS_REJECTED, "opp_val": 0, "rev": 0},
                {"corp": "Xưởng In Áo Đồng Phục Sinh Viên", "contact": "Phan Văn Đức", "phone": "0986 123 321", "camp": "CAMP-07", "days_ago": 15, "status": STATUS_ACCEPTED, "opp_val": 15000000, "rev": 0},
                {"corp": "Cá Nhân Khởi Nghiệp Dropship", "contact": "Nguyễn Quang Hải", "phone": "0907 234 432", "camp": "CAMP-07", "days_ago": 26, "status": STATUS_LOST, "opp_val": 20000000, "rev": 0}
            ]

            counter = 101
            for item in raw_leads:
                lead_id = f"LEAD-{counter}"
                counter += 1
                camp_obj = self.campaigns.get(item["camp"], {})
                source = camp_obj.get("source", "Google Ads")
                created_dt = now - timedelta(days=item["days_ago"], hours=counter % 12, minutes=counter * 3 % 50)

                lead_dict = {
                    "id": lead_id,
                    "company_name": item["corp"],
                    "contact_name": item["contact"],
                    "phone": item["phone"],
                    "email": f"{item['contact'].lower().replace(' ', '')}@example.vn",
                    "campaign_id": item["camp"],
                    "campaign_name": camp_obj.get("name", "Chiến dịch"),
                    "source": source,
                    "status": item["status"],
                    "deal_value": item["opp_val"],
                    "actual_revenue": item["rev"],
                    "created_at": created_dt,
                    "assigned_to": "usr-sales-01"
                }
                self.leads.append(lead_dict)

            self._lead_counter = counter

    # =========================================================================
    # PHƯƠNG THỨC XỬ LÝ LỌC THỜI GIAN (ACCEPTANCE CRITERIA 2)
    # =========================================================================
    def parse_date_range(self, preset=None, from_date_str=None, to_date_str=None):
        """
        Quy đổi preset hoặc chuỗi ngày YYYY-MM-DD thành cặp (from_dt, to_dt).
        Hỗ trợ:
        - 'all': Tất cả thời gian
        - 'today': Hôm nay
        - 'last_7_days': 7 ngày gần nhất
        - 'last_30_days': 30 ngày gần nhất
        - 'this_month': Tháng này
        - 'this_quarter': Quý này
        - 'custom': Theo from_date_str và to_date_str
        """
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0)
        end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59)

        if preset == "today":
            return start_of_today, end_of_today

        if preset == "last_7_days":
            return (now - timedelta(days=7)).replace(hour=0, minute=0, second=0), end_of_today

        if preset == "last_30_days":
            return (now - timedelta(days=30)).replace(hour=0, minute=0, second=0), end_of_today

        if preset == "this_month":
            start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
            return start_of_month, end_of_today

        if preset == "this_quarter":
            quarter_start_month = 3 * ((now.month - 1) // 3) + 1
            start_of_quarter = datetime(now.year, quarter_start_month, 1, 0, 0, 0)
            return start_of_quarter, end_of_today

        if preset == "custom" or (from_date_str and to_date_str):
            try:
                from_dt = datetime.strptime(from_date_str.strip(), "%Y-%m-%d")
            except Exception:
                from_dt = None

            try:
                to_dt = datetime.strptime(to_date_str.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            except Exception:
                to_dt = None

            return from_dt, to_dt

        # Mặc định preset 'all': Không giới hạn thời gian
        return None, None

    def _filter_lead_by_date(self, lead, from_dt, to_dt):
        """Kiểm tra một lead có nằm trong khoảng thời gian hay không"""
        created = lead.get("created_at")
        if not created:
            return True
        if from_dt and created < from_dt:
            return False
        if to_dt and created > to_dt:
            return False
        return True

    # =========================================================================
    # 🎯 TIÊU CHÍ 1: BÁO CÁO HIỆU QUẢ THEO NGUỒN LEAD
    # Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn
    # Doanh thu thực tế, chi phí & Khuyến nghị dồn ngân sách
    # =========================================================================
    def get_report_by_source(self, from_dt=None, to_dt=None):
        with self.lock:
            # Lọc danh sách lead theo khoảng thời gian
            filtered_leads = [l for l in self.leads if self._filter_lead_by_date(l, from_dt, to_dt)]

            # Gom nhóm theo từng nguồn
            sources_map = {s: [] for s in SOURCES}
            for l in filtered_leads:
                s = l.get("source")
                if s not in sources_map:
                    sources_map[s] = []
                sources_map[s].append(l)

            # Tính toán chỉ số chiến dịch tương ứng cho từng nguồn
            report_data = []

            for source_name, leads_in_source in sources_map.items():
                total_leads = len(leads_in_source)
                
                # 1. Số lead được Sales nhận chăm sóc (ACCEPTED, OPPORTUNITY, WON, LOST)
                accepted_leads = len([l for l in leads_in_source if l["status"] in [STATUS_ACCEPTED, STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])
                
                # 2. Tỷ lệ được nhận (%)
                acceptance_rate = round((accepted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

                # 3. Số lead chuyển đổi thành cơ hội bán hàng (OPPORTUNITY, WON, LOST)
                opp_leads = len([l for l in leads_in_source if l["status"] in [STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])

                # 4. Tỷ lệ chuyển đổi thành cơ hội (%)
                opp_conversion_rate = round((opp_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

                # 5. Số lượng chốt thành công & Doanh thu thực tế phát sinh
                won_leads = len([l for l in leads_in_source if l["status"] == STATUS_WON])
                won_rate = round((won_leads / total_leads * 100), 1) if total_leads > 0 else 0.0
                actual_revenue = sum(l.get("actual_revenue", 0) for l in leads_in_source if l["status"] == STATUS_WON)
                potential_value = sum(l.get("deal_value", 0) for l in leads_in_source)

                # Chi phí ước lượng phân bổ cho nguồn này
                source_spent = sum(c["spent"] for c in self.campaigns.values() if c["source"] == source_name)
                
                # ROAS (Doanh thu / Chi phí)
                roas = round((actual_revenue / source_spent), 2) if source_spent > 0 else 0.0

                # Khuyến nghị dồn ngân sách (Budget Allocation Recommendation)
                if roas >= 4.0 or (actual_revenue >= 200000000 and opp_conversion_rate >= 40):
                    recommendation = "⭐ DỒN NGÂN SÁCH (Hiệu quả cao, Doanh thu & ROI vượt trội)"
                    recommendation_code = "INCREASE"
                    badge_class = "badge-green"
                elif opp_conversion_rate >= 30 and roas >= 1.5:
                    recommendation = "✅ DUY TRÌ & TỐI ƯU (Hiệu quả ổn định, sinh lời tốt)"
                    recommendation_code = "MAINTAIN"
                    badge_class = "badge-blue"
                elif total_leads >= 8 and opp_conversion_rate < 25 and roas < 1.0:
                    recommendation = "⚠️ TỐI ƯU CHẤT LƯỢNG (Lead nhiều nhưng ít cơ hội & doanh thu thấp)"
                    recommendation_code = "OPTIMIZE"
                    badge_class = "badge-amber"
                elif roas < 0.5 and source_spent > 20000000:
                    recommendation = "⏸️ CẮT GIẢM / CHUYỂN NGÂN SÁCH (Chi phí cao nhưng không ra doanh thu)"
                    recommendation_code = "DECREASE"
                    badge_class = "badge-red"
                else:
                    recommendation = "🔍 TIẾP TỤC THEO DÕI"
                    recommendation_code = "MONITOR"
                    badge_class = "badge-blue"

                report_data.append({
                    "source": source_name,
                    "icon": SOURCE_ICONS.get(source_name, "📌"),
                    "color": SOURCE_COLORS.get(source_name, "#3b82f6"),
                    "total_leads": total_leads,
                    "accepted_leads": accepted_leads,
                    "acceptance_rate": acceptance_rate,
                    "opportunity_leads": opp_leads,
                    "opportunity_conversion_rate": opp_conversion_rate,
                    "won_deals": won_leads,
                    "won_rate": won_rate,
                    "potential_value": potential_value,
                    "actual_revenue": actual_revenue,
                    "spent": source_spent,
                    "roas": roas,
                    "recommendation": recommendation,
                    "recommendation_code": recommendation_code,
                    "badge_class": badge_class
                })

            # Sắp xếp mặc định theo Doanh thu thực tế giảm dần
            report_data.sort(key=lambda x: x["actual_revenue"], reverse=True)
            return report_data

    # =========================================================================
    # 🎯 TIÊU CHÍ 1: BÁO CÁO HIỆU QUẢ THEO CHIẾN DỊCH (CAMPAIGN)
    # =========================================================================
    def get_report_by_campaign(self, from_dt=None, to_dt=None):
        with self.lock:
            filtered_leads = [l for l in self.leads if self._filter_lead_by_date(l, from_dt, to_dt)]

            report_data = []

            for camp_id, camp in self.campaigns.items():
                leads_in_camp = [l for l in filtered_leads if l.get("campaign_id") == camp_id]
                total_leads = len(leads_in_camp)

                accepted_leads = len([l for l in leads_in_camp if l["status"] in [STATUS_ACCEPTED, STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])
                acceptance_rate = round((accepted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

                opp_leads = len([l for l in leads_in_camp if l["status"] in [STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])
                opp_conversion_rate = round((opp_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

                won_deals = len([l for l in leads_in_camp if l["status"] == STATUS_WON])
                actual_revenue = sum(l.get("actual_revenue", 0) for l in leads_in_camp if l["status"] == STATUS_WON)

                spent = camp.get("spent", 0)
                budget = camp.get("budget", 0)

                # Giá mỗi lead (Cost Per Lead)
                cpl = round(spent / total_leads) if total_leads > 0 else 0
                # Giá mỗi cơ hội (Cost Per Opportunity)
                cpo = round(spent / opp_leads) if opp_leads > 0 else 0
                # Tỷ lệ hoàn vốn doanh thu (ROAS)
                roas = round((actual_revenue / spent), 2) if spent > 0 else 0.0

                if roas >= 3.5:
                    recommendation = "⭐ Dồn thêm ngân sách"
                    badge_class = "badge-green"
                elif roas >= 1.2:
                    recommendation = "✅ Hiệu quả tốt"
                    badge_class = "badge-blue"
                elif opp_conversion_rate < 25 and spent > 20000000:
                    recommendation = "⚠️ Cần tối ưu nội dung & targeting"
                    badge_class = "badge-amber"
                else:
                    recommendation = "⏸️ Cân nhắc tạm dừng"
                    badge_class = "badge-red"

                report_data.append({
                    "id": camp_id,
                    "name": camp["name"],
                    "source": camp["source"],
                    "budget": budget,
                    "spent": spent,
                    "total_leads": total_leads,
                    "accepted_leads": accepted_leads,
                    "acceptance_rate": acceptance_rate,
                    "opportunity_leads": opp_leads,
                    "opportunity_conversion_rate": opp_conversion_rate,
                    "won_deals": won_deals,
                    "actual_revenue": actual_revenue,
                    "cpl": cpl,
                    "cpo": cpo,
                    "roas": roas,
                    "recommendation": recommendation,
                    "badge_class": badge_class
                })

            report_data.sort(key=lambda x: x["actual_revenue"], reverse=True)
            return report_data

    # =========================================================================
    # TỔNG HỢP TOÀN BỘ PHỄU (SUMMARY METRICS)
    # =========================================================================
    def get_summary_metrics(self, from_dt=None, to_dt=None):
        with self.lock:
            filtered_leads = [l for l in self.leads if self._filter_lead_by_date(l, from_dt, to_dt)]

            total_leads = len(filtered_leads)
            total_accepted = len([l for l in filtered_leads if l["status"] in [STATUS_ACCEPTED, STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])
            avg_acceptance_rate = round((total_accepted / total_leads * 100), 1) if total_leads > 0 else 0.0

            total_opps = len([l for l in filtered_leads if l["status"] in [STATUS_OPPORTUNITY, STATUS_WON, STATUS_LOST]])
            avg_opp_rate = round((total_opps / total_leads * 100), 1) if total_leads > 0 else 0.0

            total_won = len([l for l in filtered_leads if l["status"] == STATUS_WON])
            total_revenue = sum(l.get("actual_revenue", 0) for l in filtered_leads if l["status"] == STATUS_WON)
            total_spent = sum(c["spent"] for c in self.campaigns.values())
            overall_roas = round((total_revenue / total_spent), 2) if total_spent > 0 else 0.0

            # Tìm nguồn tạo doanh thu cao nhất
            source_reports = self.get_report_by_source(from_dt, to_dt)
            top_revenue_source = source_reports[0]["source"] if source_reports and source_reports[0]["actual_revenue"] > 0 else "Chưa có"
            top_roas_source = max(source_reports, key=lambda x: x["roas"])["source"] if source_reports else "Chưa có"

            return {
                "total_leads": total_leads,
                "total_accepted": total_accepted,
                "avg_acceptance_rate": avg_acceptance_rate,
                "total_opps": total_opps,
                "avg_opp_rate": avg_opp_rate,
                "total_won": total_won,
                "total_revenue": total_revenue,
                "total_spent": total_spent,
                "overall_roas": overall_roas,
                "top_revenue_source": top_revenue_source,
                "top_roas_source": top_roas_source
            }

    # =========================================================================
    # DANH SÁCH LEAD CHI TIẾT CÓ BỘ LỌC
    # =========================================================================
    def get_leads_filtered(self, from_dt=None, to_dt=None, source=None, campaign_id=None, status=None):
        with self.lock:
            result = [l for l in self.leads if self._filter_lead_by_date(l, from_dt, to_dt)]
            if source:
                result = [l for l in result if l.get("source") == source]
            if campaign_id:
                result = [l for l in result if l.get("campaign_id") == campaign_id]
            if status:
                result = [l for l in result if l.get("status") == status]
            result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
            return result


# Singleton DB
db = Database()
