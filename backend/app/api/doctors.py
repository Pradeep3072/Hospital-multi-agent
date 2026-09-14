import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.doctor_service import DoctorService

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("")
def list_doctors(
    query: Optional[str] = None,
    specialty: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return DoctorService.search_doctors(db, query=query, specialty=specialty, department_name=department)


@router.get("/{doctor_id}")
def get_doctor_details(doctor_id: int, db: Session = Depends(get_db)):
    doc = DoctorService.get_doctor_details(db, doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doc


@router.get("/{doctor_id}/slots")
def get_doctor_available_slots(
    doctor_id: int,
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    slots = DoctorService.get_available_slots(db, doctor_id, target_date)
    return {
        "doctor_id": doctor_id,
        "date": date,
        "day_of_week": target_date.strftime("%A"),
        "slots": slots
    }
