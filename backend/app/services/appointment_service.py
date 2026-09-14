import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.database.models import Appointment, Patient, Doctor
from backend.app.services.doctor_service import DoctorService
from backend.app.services.notification_service import NotificationService
from backend.app.services.audit_service import AuditService


class SlotConflictError(Exception):
    pass


class AppointmentNotFoundError(Exception):
    pass


class InvalidOperationError(Exception):
    pass


class AppointmentService:
    @staticmethod
    def book_appointment(
        db: Session,
        patient_id: int,
        doctor_id: int,
        appointment_date: datetime.date,
        appointment_time: datetime.time,
        reason_for_visit: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically books an appointment with database concurrency protection.
        Prevents race conditions and double-booking.
        """
        # 1. Validate patient
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise InvalidOperationError(f"Patient with ID {patient_id} does not exist.")

        # 2. Validate doctor
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            raise InvalidOperationError(f"Doctor with ID {doctor_id} does not exist.")

        # 3. Check availability window
        available_slots = DoctorService.get_available_slots(db, doctor_id, appointment_date)
        time_str = appointment_time.strftime("%H:%M")
        if time_str not in available_slots:
            raise SlotConflictError(f"Time slot {time_str} on {appointment_date} is not available for Dr. {doctor.user.full_name}.")

        # 4. Atomic PostgreSQL/Database Transaction
        try:
            # Check for conflict right before inserting
            existing = db.query(Appointment).filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
                Appointment.status.in_(["CONFIRMED", "PENDING"])
            ).first()

            if existing:
                raise SlotConflictError(f"Slot {time_str} is already reserved.")

            appt = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                status="CONFIRMED",
                reason_for_visit=reason_for_visit or "General Consultation"
            )
            db.add(appt)
            db.commit()
            db.refresh(appt)

        except IntegrityError:
            db.rollback()
            raise SlotConflictError(f"Race condition detected: Slot {time_str} on {appointment_date} was just booked by another patient.")
        except Exception:
            db.rollback()
            raise

        # 5. Audit log
        AuditService.log_action(
            db=db,
            action="BOOK_APPOINTMENT",
            resource="Appointment",
            details=f"Appointment {appt.id} booked for patient {patient_id} with doctor {doctor_id}",
            user_id=patient.user_id
        )

        # 6. Async notification
        doc_name = doctor.user.full_name if doctor.user else f"Doctor {doctor_id}"
        NotificationService.send_booking_confirmation(
            db=db,
            user_id=patient.user_id,
            recipient=patient.user.email if patient.user else "patient@example.com",
            appointment_id=appt.id,
            doctor_name=doc_name,
            appointment_date=str(appointment_date),
            appointment_time=time_str
        )

        return {
            "appointment_id": appt.id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "doctor_name": doc_name,
            "date": str(appointment_date),
            "time": time_str,
            "status": appt.status,
            "reason_for_visit": appt.reason_for_visit
        }

    @staticmethod
    def cancel_appointment(db: Session, appointment_id: int, patient_id: Optional[int] = None) -> Dict[str, Any]:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise AppointmentNotFoundError(f"Appointment with ID {appointment_id} not found.")

        if patient_id and appt.patient_id != patient_id:
            raise InvalidOperationError("Unauthorized: You cannot cancel another patient's appointment.")

        if appt.status == "CANCELLED":
            return {"appointment_id": appt.id, "status": "ALREADY_CANCELLED", "message": "Appointment is already cancelled."}

        appt.status = "CANCELLED"
        db.commit()

        # Audit log
        AuditService.log_action(
            db=db,
            action="CANCEL_APPOINTMENT",
            resource="Appointment",
            details=f"Appointment {appointment_id} cancelled",
            user_id=appt.patient.user_id if appt.patient else None
        )

        # Send cancellation notification
        if appt.patient and appt.patient.user:
            doc_name = appt.doctor.user.full_name if appt.doctor and appt.doctor.user else "Doctor"
            NotificationService.send_cancellation_notice(
                db=db,
                user_id=appt.patient.user_id,
                recipient=appt.patient.user.email,
                appointment_id=appt.id,
                doctor_name=doc_name,
                appointment_date=str(appt.appointment_date)
            )

        return {
            "appointment_id": appt.id,
            "status": "CANCELLED",
            "message": f"Appointment with Dr. {appt.doctor.user.full_name if appt.doctor and appt.doctor.user else ''} has been successfully cancelled."
        }

    @staticmethod
    def reschedule_appointment(
        db: Session,
        appointment_id: int,
        new_date: datetime.date,
        new_time: datetime.time,
        patient_id: Optional[int] = None
    ) -> Dict[str, Any]:
        appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appt:
            raise AppointmentNotFoundError(f"Appointment with ID {appointment_id} not found.")

        if patient_id and appt.patient_id != patient_id:
            raise InvalidOperationError("Unauthorized: You cannot reschedule another patient's appointment.")

        # Check new slot availability
        available_slots = DoctorService.get_available_slots(db, appt.doctor_id, new_date)
        time_str = new_time.strftime("%H:%M")
        if time_str not in available_slots:
            raise SlotConflictError(f"New slot {time_str} on {new_date} is not available.")

        # Update in transaction
        try:
            appt.appointment_date = new_date
            appt.appointment_time = new_time
            appt.status = "CONFIRMED"
            db.commit()
            db.refresh(appt)
        except IntegrityError:
            db.rollback()
            raise SlotConflictError("Target slot was just reserved by another request.")

        # Audit log
        AuditService.log_action(
            db=db,
            action="RESCHEDULE_APPOINTMENT",
            resource="Appointment",
            details=f"Appointment {appointment_id} rescheduled to {new_date} {time_str}",
            user_id=appt.patient.user_id if appt.patient else None
        )

        return {
            "appointment_id": appt.id,
            "date": str(appt.appointment_date),
            "time": time_str,
            "status": appt.status,
            "message": f"Appointment successfully rescheduled to {new_date} at {time_str}."
        }
