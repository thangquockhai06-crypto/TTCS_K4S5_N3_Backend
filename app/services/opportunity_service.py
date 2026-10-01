"""
OpportunityService là bí danh (alias) của DealService để hỗ trợ đồng nhất Deals / Opportunities.
"""
from app.services.deal_service import DealService

class OpportunityService(DealService):
    """Kế thừa toàn bộ hành vi từ DealService."""
    pass
