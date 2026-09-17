import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.database.models import Appointment, Patient, Doctor
from backend.app.services.doctor_service import DoctorService
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
        patient_id: Optional[int] = None,
        doctor_id: int = 1,
        appointment_date: datetime.date = None,
        appointment_time: datetime.time = None,
        reason_for_visit: Optional[str] = None,
        patient_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically books an appointment with database concurrency protection.
        Prevents race conditions and double-booking.
        """
        # 1. Validate or resolve patient
        patient = None
        if patient_id:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient and patient_name:
            clean_name = patient_name.strip()
            patient = db.query(Patient).filter(Patient.full_name.ilike(f"%{clean_name}%")).first()
            if not patient and clean_name:
                # Create patient on the fly
                patient = Patient(
                    full_name=clean_name,
                    date_of_birth=datetime.date(1990, 1, 1),
                    gender="Not Specified"
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

        if not patient:
            # Fallback to default active patient if none specified
            patient = db.query(Patient).first()
            if not patient:
                raise InvalidOperationError("No registered patients found.")

        # 2. Validate doctor
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            raise InvalidOperationError(f"Doctor with ID {doctor_id} does not exist.")

        # 3. Check availability window
        available_slots = DoctorService.get_available_slots(db, doctor_id, appointment_date)
        time_str = appointment_time.strftime("%H:%M")
        if time_str not in available_slots:
            raise SlotConflictError(f"Time slot {time_str} on {appointment_date} is not available for Dr. {doctor.full_name}.")

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

            patient_id = patient.id
            appt = Appointment(
                patient_id=patient.id,
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
            details=f"Appointment {appt.id} booked for patient {patient.id} ({patient.full_name}) with doctor {doctor_id}",
            patient_id=patient.id
        )

        doc_name = doctor.full_name if doctor else f"Doctor {doctor_id}"

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
            patient_id=appt.patient_id if appt else None
        )

        doc_name = appt.doctor.full_name if appt.doctor else ""

        return {
            "appointment_id": appt.id,
            "status": "CANCELLED",
            "message": f"Appointment with Dr. {doc_name} has been successfully cancelled."
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
            patient_id=appt.patient_id if appt else None
        )

        return {
            "appointment_id": appt.id,
            "date": str(appt.appointment_date),
            "time": time_str,
            "status": appt.status,
            "message": f"Appointment successfully rescheduled to {new_date} at {time_str}."
        }
