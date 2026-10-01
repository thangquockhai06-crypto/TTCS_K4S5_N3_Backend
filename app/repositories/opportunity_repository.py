"""
OpportunityRepository là bí danh (alias) của DealRepository để hỗ trợ đồng nhất thuật ngữ Deals / Opportunities.
"""
from app.repositories.deal_repository import DealRepository

class OpportunityRepository(DealRepository):
    """Kế thừa toàn bộ hành vi từ DealRepository."""
    pass
