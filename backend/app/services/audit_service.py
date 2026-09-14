from sqlalchemy.orm import Session
from backend.app.database.models import AuditLog


class AuditService:
    @staticmethod
    def log_action(db: Session, action: str, resource: str, details: str = None, user_id: int = None, ip_address: str = "127.0.0.1"):
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                details=details,
                ip_address=ip_address
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Failed to record audit log: {e}")
