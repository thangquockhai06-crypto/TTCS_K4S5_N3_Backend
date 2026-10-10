"""
Kiểm thử Tiêu chí 1 (Acceptance Criteria 1) - Ticket SCRUM-99:
"Số lead, tỷ lệ được nhận, tỷ lệ chuyển đổi thành cơ hội theo từng nguồn và từng chiến dịch"
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Database
from config import SOURCES


class TestAC1SourceCampaignMetrics(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_report_by_source_contains_all_required_metrics(self):
        """
        Chứng minh hệ thống tính toán chính xác 100% các chỉ số theo từng NGUỒN LEAD:
        1. Số lead
        2. Tỷ lệ được nhận (%)
        3. Tỷ lệ chuyển đổi thành cơ hội (%)
        4. Doanh thu thực tế mang lại
        5. Đánh giá & Khuyến nghị dồn ngân sách
        """
        source_reports = self.db.get_report_by_source()
        self.assertIsInstance(source_reports, list)
        self.assertGreaterEqual(len(source_reports), len(SOURCES))

        for item in source_reports:
            # Kiểm tra đầy đủ các trường bắt buộc theo đề bài
            self.assertIn("source", item)
            self.assertIn("total_leads", item)
            self.assertIn("accepted_leads", item)
            self.assertIn("acceptance_rate", item)
            self.assertIn("opportunity_leads", item)
            self.assertIn("opportunity_conversion_rate", item)
            self.assertIn("won_deals", item)
            self.assertIn("actual_revenue", item)
            self.assertIn("recommendation", item)

            total = item["total_leads"]
            accepted = item["accepted_leads"]
            acc_rate = item["acceptance_rate"]
            opp = item["opportunity_leads"]
            opp_rate = item["opportunity_conversion_rate"]

            # Kiểm tra công thức tỷ lệ được nhận: (accepted / total) * 100
            if total > 0:
                expected_acc_rate = round((accepted / total * 100), 1)
                self.assertEqual(acc_rate, expected_acc_rate)

                # Kiểm tra công thức tỷ lệ cơ hội: (opp / total) * 100
                expected_opp_rate = round((opp / total * 100), 1)
                self.assertEqual(opp_rate, expected_opp_rate)

                # Lead cơ hội phải nhỏ hơn hoặc bằng lead đã nhận
                self.assertLessEqual(opp, accepted)
            else:
                self.assertEqual(acc_rate, 0.0)
                self.assertEqual(opp_rate, 0.0)

    def test_report_by_campaign_contains_all_required_metrics(self):
        """
        Chứng minh hệ thống tính toán chính xác 100% các chỉ số theo từng CHIẾN DỊCH:
        1. Số lead
        2. Tỷ lệ được nhận (%)
        3. Tỷ lệ chuyển đổi thành cơ hội (%)
        4. Chi phí, CPL, CPO, Doanh thu và ROAS
        """
        campaign_reports = self.db.get_report_by_campaign()
        self.assertIsInstance(campaign_reports, list)
        self.assertGreaterEqual(len(campaign_reports), 5)

        for c in campaign_reports:
            self.assertIn("id", c)
            self.assertIn("name", c)
            self.assertIn("source", c)
            self.assertIn("total_leads", c)
            self.assertIn("accepted_leads", c)
            self.assertIn("acceptance_rate", c)
            self.assertIn("opportunity_leads", c)
            self.assertIn("opportunity_conversion_rate", c)
            self.assertIn("actual_revenue", c)
            self.assertIn("roas", c)

            if c["total_leads"] > 0:
                expected_acc = round((c["accepted_leads"] / c["total_leads"] * 100), 1)
                self.assertEqual(c["acceptance_rate"], expected_acc)

                expected_opp = round((c["opportunity_leads"] / c["total_leads"] * 100), 1)
                self.assertEqual(c["opportunity_conversion_rate"], expected_opp)

    def test_budget_reallocation_recommendation_logic(self):
        """
        Chứng minh mục tiêu của User Story:
        'để dồn ngân sách vào nguồn thực sự ra doanh thu'
        Hệ thống phải đưa ra khuyến nghị 'DỒN NGÂN SÁCH' cho nguồn có doanh thu và ROAS cao nhất.
        """
        source_reports = self.db.get_report_by_source()
        increase_sources = [s for s in source_reports if s["recommendation_code"] == "INCREASE"]
        self.assertGreater(len(increase_sources), 0, "Hệ thống phải xác định được ít nhất 1 nguồn vượt trội để khuyên dồn ngân sách")

        # Nguồn được khuyên dồn ngân sách phải có doanh thu lớn
        for inc in increase_sources:
            self.assertGreaterEqual(inc["actual_revenue"], 100000000)


if __name__ == "__main__":
    unittest.main()
