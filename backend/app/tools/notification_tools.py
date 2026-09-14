from typing import Dict, Any
from backend.app.database.session import SessionLocal
from backend.app.services.notification_service import NotificationService


def send_email(user_id: int, recipient: str, subject: str, message: str) -> Dict[str, Any]:
    """
    Send an email notification to a patient or staff member.
    """
    db = SessionLocal()
    try:
        notif = NotificationService.send_notification(
            db=db, user_id=user_id, recipient=recipient, subject=subject, message=message, channel="email"
        )
        return {"status": "success", "notification_id": notif.id, "channel": "email"}
    finally:
        db.close()


def send_sms(user_id: int, phone: str, message: str) -> Dict[str, Any]:
    """
    Send an SMS notification to a patient's mobile device.
    """
    db = SessionLocal()
    try:
        notif = NotificationService.send_notification(
            db=db, user_id=user_id, recipient=phone, subject="SMS Alert", message=message, channel="sms"
        )
        return {"status": "success", "notification_id": notif.id, "channel": "sms"}
    finally:
        db.close()


def create_notification(user_id: int, message: str, channel: str = "push") -> Dict[str, Any]:
    """
    Create an in-app or push notification.
    """
    db = SessionLocal()
    try:
        notif = NotificationService.send_notification(
            db=db, user_id=user_id, recipient=f"user_{user_id}", subject="Hospital Notice", message=message, channel=channel
        )
        return {"status": "success", "notification_id": notif.id}
    finally:
        db.close()
