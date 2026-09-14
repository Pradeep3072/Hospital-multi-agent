import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.appointment_service import (
    AppointmentService, SlotConflictError, AppointmentNotFoundError, InvalidOperationError
)
from backend.app.schemas.appointment import BookAppointmentRequest, RescheduleAppointmentRequest, CancelAppointmentRequest

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/book")
def book_appointment(req: BookAppointmentRequest, db: Session = Depends(get_db)):
    try:
        appt_date = datetime.date.fromisoformat(req.date)
        parts = req.time.split(":")
        appt_time = datetime.time(int(parts[0]), int(parts[1]))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date or time format.")

    try:
        return AppointmentService.book_appointment(
            db=db,
            patient_id=req.patient_id,
            doctor_id=req.doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            reason_for_visit=req.reason
        )
    except SlotConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, req: CancelAppointmentRequest = None, db: Session = Depends(get_db)):
    patient_id = req.patient_id if req else None
    try:
        return AppointmentService.cancel_appointment(db, appointment_id, patient_id)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_id}/reschedule")
def reschedule_appointment(appointment_id: int, req: RescheduleAppointmentRequest, db: Session = Depends(get_db)):
    try:
        new_date = datetime.date.fromisoformat(req.new_date)
        parts = req.new_time.split(":")
        new_time = datetime.time(int(parts[0]), int(parts[1]))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date or time format.")

    try:
        return AppointmentService.reschedule_appointment(
            db=db,
            appointment_id=appointment_id,
            new_date=new_date,
            new_time=new_time,
            patient_id=req.patient_id
        )
    except SlotConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
