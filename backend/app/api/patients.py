from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("")
def list_patients(db: Session = Depends(get_db)):
    return PatientService.list_all_patients(db)


@router.get("/{patient_id}")
def get_patient_profile(patient_id: int, db: Session = Depends(get_db)):
    profile = PatientService.get_patient_profile(db, patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")
    return profile


@router.get("/{patient_id}/appointments")
def get_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    return PatientService.get_patient_appointments(db, patient_id)


@router.get("/{patient_id}/records")
def get_patient_records(patient_id: int, db: Session = Depends(get_db)):
    return PatientService.get_patient_records(db, patient_id)


@router.get("/{patient_id}/prescriptions")
def get_patient_prescriptions(patient_id: int, db: Session = Depends(get_db)):
    return PatientService.get_patient_prescriptions(db, patient_id)
