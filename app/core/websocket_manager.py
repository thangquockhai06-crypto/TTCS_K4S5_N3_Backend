import json
import logging
from typing import Dict, List, Any
from fastapi import WebSocket

logger = logging.getLogger("nexuscrm.websocket")


class WebSocketNotificationManager:
    """
    Quản lý các kết nối WebSocket thời gian thực cho tính năng In-app Notifications.
    Hỗ trợ phát thông báo trực tiếp tới tài khoản nhân viên / trưởng nhóm ngay khi có sự kiện.
    """

    def __init__(self):
        # user_id -> List[WebSocket] (hỗ trợ 1 user mở nhiều tab trình duyệt)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"[WEBSOCKET] User {user_id} đã kết nối WebSocket. Tổng tabs: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[WEBSOCKET] User {user_id} đã ngắt kết nối WebSocket.")

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Gửi thông báo thời gian thực tới tất cả các tab đang mở của một user."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message, default=str))
                except Exception as e:
                    logger.warning(f"[WEBSOCKET ERROR] Lỗi gửi thông điệp tới user {user_id}: {e}")
                    dead_connections.append(connection)

            for dead in dead_connections:
                self.disconnect(dead, user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Phát thông báo tới toàn bộ người dùng đang online."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(user_id, message)


notification_manager = WebSocketNotificationManager()

