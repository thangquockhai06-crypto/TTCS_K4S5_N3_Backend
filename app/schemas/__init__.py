from app.schemas.auth import (
    LoginPayload,
    RegisterPayload,
    RefreshTokenPayload,
    UserDTO,
    AuthResponse,
    RefreshTokenResponseDTO,
    MessageResponse,
)
from app.schemas.customer import (
    CustomerDTO,
    CreateCustomerDTO,
    UpdateCustomerDTO,
    UpdateCustomerStatusDTO,
    CustomerNoteCreateDTO,
    CustomerActivityCreateDTO,
    CustomerMergeDTO,
    CustomerHierarchyDTO,
    StagnantCustomerDTO,
    RiskScanResultDTO,
)
from app.schemas.contact import (
    ContactDTO,
    ContactCreateDTO,
    ContactUpdateDTO,
    TransferContactDTO,
)
from app.schemas.support_ticket import (
    SupportTicketDTO,
    CreateSupportTicketDTO,
    UpdateSupportTicketDTO,
)
from app.schemas.saved_filter import (
    SavedFilterPresetDTO,
    CreateSavedFilterDTO,
)
from app.schemas.customer_360 import (
    Customer360DTO,
)
from app.schemas.deal import (
    DealDTO,
    CreateDealDTO,
    MoveDealStageDTO,
)

__all__ = [
    "LoginPayload",
    "RegisterPayload",
    "RefreshTokenPayload",
    "UserDTO",
    "AuthResponse",
    "RefreshTokenResponseDTO",
    "MessageResponse",
    "CustomerDTO",
    "CreateCustomerDTO",
    "UpdateCustomerDTO",
    "UpdateCustomerStatusDTO",
    "CustomerNoteCreateDTO",
    "CustomerActivityCreateDTO",
    "CustomerMergeDTO",
    "CustomerHierarchyDTO",
    "StagnantCustomerDTO",
    "RiskScanResultDTO",
    "ContactDTO",
    "ContactCreateDTO",
    "ContactUpdateDTO",
    "TransferContactDTO",
    "SupportTicketDTO",
    "CreateSupportTicketDTO",
    "UpdateSupportTicketDTO",
    "SavedFilterPresetDTO",
    "CreateSavedFilterDTO",
    "Customer360DTO",
    "DealDTO",
    "CreateDealDTO",
    "MoveDealStageDTO",
]
