from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.token import RefreshToken

class TokenRepository:
    """
    Tầng Repository xử lý truy vấn phiên làm việc & Refresh Token (SCRUM-34 / SCRUM-103).
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def create(db: Session, refresh_token: RefreshToken) -> RefreshToken:
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        return refresh_token

    @staticmethod
    def get_by_token_and_user_id(db: Session, token_str: str, user_id: str) -> Optional[RefreshToken]:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token_str,
                RefreshToken.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def revoke_token(db: Session, token_record: RefreshToken) -> None:
        token_record.is_revoked = True
        db.commit()
        db.refresh(token_record)

    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: str, specific_token: Optional[str] = None) -> int:
        query = db.query(RefreshToken).filter(RefreshToken.user_id == user_id)
        if specific_token:
            query = query.filter(RefreshToken.token == specific_token)

        tokens: List[RefreshToken] = query.all()
        for t in tokens:
            t.is_revoked = True

        db.commit()
        return len(tokens)

    @staticmethod
    def revoke_other_user_tokens(db: Session, user_id: str, keep_token: Optional[str] = None) -> int:
        """
        [SCRUM-72 / S1-04] Thu hồi các phiên đăng nhập khác của người dùng.
        """
        query = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
        if keep_token:
            query = query.filter(RefreshToken.token != keep_token)

        tokens: List[RefreshToken] = query.all()
        for t in tokens:
            t.is_revoked = True

        db.commit()
        return len(tokens)

