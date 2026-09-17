import datetime
from typing import Dict, Any, List, Optional
from backend.app.database.session import SessionLocal
from backend.app.services.doctor_service import DoctorService


def search_doctors(
    query: Optional[str] = None,
    specialty: Optional[str] = None,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search hospital doctors by name, medical specialty, or department.
    """
    db = SessionLocal()
    try:
        doctors = DoctorService.search_doctors(db, query=query, specialty=specialty, department_name=department)
        return {"status": "success", "count": len(doctors), "doctors": doctors}
    finally:
        db.close()


def get_doctor_details(doctor_id: int) -> Dict[str, Any]:
    """
    Get full profile, qualifications, and consultation fee for a doctor.
    """
    db = SessionLocal()
    try:
        details = DoctorService.get_doctor_details(db, doctor_id)
        if not details:
            return {"status": "error", "message": f"Doctor with ID {doctor_id} not found."}
        return {"status": "success", "doctor": details}
    finally:
        db.close()


def get_doctor_schedule(doctor_id: int) -> Dict[str, Any]:
    """
    Get recurring weekly schedule and any upcoming planned leaves for a doctor.
    """
    db = SessionLocal()
    try:
        details = DoctorService.get_doctor_details(db, doctor_id)
        if not details:
            return {"status": "error", "message": f"Doctor with ID {doctor_id} not found."}
        return {
            "status": "success",
            "doctor_id": doctor_id,
            "doctor_name": details["name"],
            "schedules": details["schedules"],
            "leaves": details["leaves"]
        }
    finally:
        db.close()


def get_available_slots(doctor_id: int, date_str: str) -> Dict[str, Any]:
    """
    Get open consultation slots for a doctor on a specific date (YYYY-MM-DD).
    """
    db = SessionLocal()
    try:
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return {"status": "error", "message": f"Invalid date format '{date_str}'. Please use YYYY-MM-DD."}

        slots = DoctorService.get_available_slots(db, doctor_id, target_date)
        return {
            "status": "success",
            "doctor_id": doctor_id,
            "date": date_str,
            "day_of_week": target_date.strftime("%A"),
            "available_slots_count": len(slots),
            "slots": slots
        }
    finally:
        db.close()


def get_available_doctors_by_date(
    date_str: str,
    specialty: Optional[str] = None,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all hospital doctors who have open consultation slots on a specific date (YYYY-MM-DD),
    along with their open time slots.
    """
    db = SessionLocal()
    try:
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return {"status": "error", "message": f"Invalid date format '{date_str}'. Please use YYYY-MM-DD."}

        docs = DoctorService.get_available_doctors_on_date(
            db,
            target_date=target_date,
            specialty=specialty,
            department_name=department
        )
        return {
            "status": "success",
            "date": date_str,
            "day_of_week": target_date.strftime("%A"),
            "specialty_filter": specialty,
            "count": len(docs),
            "doctors": docs
        }
    finally:
        db.close()

