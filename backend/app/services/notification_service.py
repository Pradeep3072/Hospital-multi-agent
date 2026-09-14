import datetime
from sqlalchemy.orm import Session
from backend.app.database.models import Notification


class NotificationService:
    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        recipient: str,
        subject: str,
        message: str,
        channel: str = "email"
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            message=message,
            status="SENT",
            sent_at=datetime.datetime.utcnow()
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        print(f"[Notification Worker] [{channel.upper()}] Sent to {recipient}: '{subject}'")
        return notif

    @staticmethod
    def send_booking_confirmation(
        db: Session,
        user_id: int,
        recipient: str,
        appointment_id: int,
        doctor_name: str,
        appointment_date: str,
        appointment_time: str
    ):
        subject = f"Appointment Confirmation - HopeCare Hospital (#{appointment_id})"
        message = (
            f"Dear Patient,\n\nYour appointment with {doctor_name} has been successfully confirmed for "
            f"{appointment_date} at {appointment_time}.\n\n"
            f"Location: HopeCare General Hospital, Main Clinic Wing.\n"
            f"Please arrive 15 minutes prior to your scheduled time.\n\n"
            f"Regards,\nHopeCare Hospital Management"
        )
        return NotificationService.send_notification(db, user_id, recipient, subject, message)

    @staticmethod
    def send_cancellation_notice(
        db: Session,
        user_id: int,
        recipient: str,
        appointment_id: int,
        doctor_name: str,
        appointment_date: str
    ):
        subject = f"Appointment Cancelled - HopeCare Hospital (#{appointment_id})"
        message = (
            f"Dear Patient,\n\nYour appointment with {doctor_name} scheduled for {appointment_date} "
            f"has been cancelled.\nIf you wish to reschedule, you can chat with our AI assistant or visit our portal."
        )
        return NotificationService.send_notification(db, user_id, recipient, subject, message)
