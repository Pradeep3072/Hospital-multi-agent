from typing import Dict, Any, List, Optional
from backend.app.database.session import SessionLocal
from backend.app.services.patient_service import PatientService


def get_current_patient(patient_id: int) -> Dict[str, Any]:
    """
    Get profile overview for the authenticated/active patient.
    """
    db = SessionLocal()
    try:
        profile = PatientService.get_patient_profile(db, patient_id)
        if not profile:
            return {"status": "error", "message": f"Patient with ID {patient_id} not found."}
        return {"status": "success", "patient": profile}
    finally:
        db.close()


def get_patient_profile(patient_id: int) -> Dict[str, Any]:
    """
    Detailed patient profile including emergency contacts and insurance policy.
    """
    return get_current_patient(patient_id)


def get_patient_appointments(patient_id: int) -> Dict[str, Any]:
    """
    Retrieve all upcoming and past appointments for the active patient.
    """
    db = SessionLocal()
    try:
        appts = PatientService.get_patient_appointments(db, patient_id)
        return {"status": "success", "count": len(appts), "appointments": appts}
    finally:
        db.close()


def get_patient_records(patient_id: int) -> Dict[str, Any]:
    """
    Retrieve past medical diagnoses and treatment summaries for the active patient.
    """
    db = SessionLocal()
    try:
        records = PatientService.get_patient_records(db, patient_id)
        return {"status": "success", "records": records}
    finally:
        db.close()


def get_patient_prescriptions(patient_id: int) -> Dict[str, Any]:
    """
    Retrieve current and past active medication prescriptions for the active patient.
    """
    db = SessionLocal()
    try:
        prescriptions = PatientService.get_patient_prescriptions(db, patient_id)
        return {"status": "success", "prescriptions": prescriptions}
    finally:
        db.close()
