"""
Kiểm thử Tiêu chí 3 (Acceptance Criteria 3) - Ticket SCRUM-99:
"Xuất Excel"
"""

import sys
import os
import unittest
import openpyxl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from excel_exporter import generate_excel_report


class TestAC3ExcelExport(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_generate_excel_report_returns_valid_xlsx(self):
        """
        Chứng minh hệ thống xuất ra file Excel (.xlsx) hợp lệ:
        1. Buffer dữ liệu không rỗng và có dung lượng hợp lệ
        2. Mở được trực tiếp bằng thư viện openpyxl
        3. Có đầy đủ 3 Sheet:
           - 'Hiệu Quả Nguồn Lead'
           - 'Hiệu Quả Chiến Dịch'
           - 'Danh Sách Lead Chi Tiết'
        """
        excel_buffer = generate_excel_report(self.db, date_label="Toàn bộ thời gian")
        self.assertIsNotNone(excel_buffer)
        
        # Đọc lại từ buffer bằng openpyxl để xác thực cấu trúc file Excel
        wb = openpyxl.load_workbook(excel_buffer)
        sheet_names = wb.sheetnames

        self.assertIn("Hiệu Quả Nguồn Lead", sheet_names)
        self.assertIn("Hiệu Quả Chiến Dịch", sheet_names)
        self.assertIn("Danh Sách Lead Chi Tiết", sheet_names)

        # Kiểm tra nội dung Sheet 1 (Hiệu Quả Nguồn Lead)
        ws1 = wb["Hiệu Quả Nguồn Lead"]
        self.assertEqual(ws1["A1"].value, "BÁO CÁO HIỆU QUẢ TỪNG NGUỒN LEAD & ĐÁNH GIÁ DOANH THU")
        
        # Tiêu đề cột hàng 4
        headers_in_sheet = [ws1.cell(row=4, column=col).value for col in range(1, 13)]
        self.assertIn("Nguồn Lead", headers_in_sheet)
        self.assertIn("Số Lead", headers_in_sheet)
        self.assertIn("Tỷ Lệ Nhận (%)", headers_in_sheet)
        self.assertIn("Tỷ Lệ Ra Cơ Hội (%)", headers_in_sheet)
        self.assertIn("Doanh Thu Thực Tế (VNĐ)", headers_in_sheet)
        self.assertIn("Đánh Giá & Khuyến Nghị Dồn Ngân Sách", headers_in_sheet)

        # Đảm bảo có dữ liệu nguồn lead trong bảng
        found_google = False
        for row in range(5, ws1.max_row):
            if ws1.cell(row=row, column=2).value == "Google Ads":
                found_google = True
                # Kiểm tra số lead và tỷ lệ có giá trị
                self.assertGreater(ws1.cell(row=row, column=3).value, 0)
                break
        self.assertTrue(found_google, "File Excel phải chứa dòng dữ liệu của nguồn Google Ads")

    def test_excel_export_respects_filtered_date_range(self):
        """
        Chứng minh khi xuất Excel kèm bộ lọc thời gian:
        Dữ liệu trong các sheet của Excel phản ánh chính xác khoảng thời gian lọc.
        """
        f_7, t_7 = self.db.parse_date_range(preset="last_7_days")
        excel_buffer = generate_excel_report(self.db, from_dt=f_7, to_dt=t_7, date_label="7 ngày qua")

        wb = openpyxl.load_workbook(excel_buffer)
        ws3 = wb["Danh Sách Lead Chi Tiết"]
        
        # Kiểm tra tiêu đề có ghi nhãn bộ lọc
        self.assertIn("7 ngày qua", ws3["A2"].value)

        # Số dòng dữ liệu lead chi tiết phải khớp với số lead trong 7 ngày
        leads_7 = self.db.get_leads_filtered(from_dt=f_7, to_dt=t_7)
        # Hàng 4 là header, từ hàng 5 là dữ liệu
        data_rows_count = ws3.max_row - 4
        self.assertEqual(data_rows_count, len(leads_7))


if __name__ == "__main__":
    unittest.main()
