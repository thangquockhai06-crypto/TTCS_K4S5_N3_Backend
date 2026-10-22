from pydantic import BaseModel
class UserNotificationPreferenceDTO(BaseModel):
    inAppEnabled: bool = True
