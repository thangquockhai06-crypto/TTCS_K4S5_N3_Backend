from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.customers import router as customers_router
from app.routers.contacts import router as contacts_router
from app.routers.support_tickets import router as support_tickets_router
from app.routers.saved_filters import router as saved_filters_router
from app.routers.deals import router as deals_router
from app.routers.opportunities import router as opportunities_router
from app.routers.activities import router as activities_router
from app.routers.quotations import router as quotations_router
from app.routers.dashboard import router as dashboard_router
from app.routers.audit_logs import router as audit_logs_router
from app.routers.products import router as products_router
from app.routers.categories import router as categories_router
from app.routers.org_tree import router as org_tree_router
from app.routers.custom_fields import router as custom_fields_router
from app.routers.pipelines import router as pipelines_router
from app.routers.win_loss import router as win_loss_router
from app.routers.user_import import router as user_import_router
from app.routers.leads import router as leads_router
from app.routers.campaigns import router as campaigns_router

__all__ = [
    "auth_router",
    "users_router",
    "customers_router",
    "contacts_router",
    "support_tickets_router",
    "saved_filters_router",
    "deals_router",
    "opportunities_router",
    "activities_router",
    "quotations_router",
    "dashboard_router",
    "audit_logs_router",
    "products_router",
    "categories_router",
    "org_tree_router",
    "custom_fields_router",
    "pipelines_router",
    "win_loss_router",
    "user_import_router",
    "leads_router",
    "campaigns_router",
]
