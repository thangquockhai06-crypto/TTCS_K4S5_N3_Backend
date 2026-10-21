from typing import Dict, Any
from app.core.websocket_manager import notification_manager


class NotificationBroadcastService:
    @staticmethod
    async def broadcast_to_user(user_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
        message = {
            "event": event_type,
            "data": payload,
        }
        await notification_manager.send_personal_message(user_id, message)
        return True
