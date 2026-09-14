import datetime
from typing import Dict, Any, Optional
from backend.app.database.session import SessionLocal
from backend.app.services.appointment_service import (
    AppointmentService, SlotConflictError, AppointmentNotFoundError, InvalidOperationError
)


def check_availability(doctor_id: int, date_str: str) -> Dict[str, Any]:
    """
    Check doctor's available appointment slots on a given date (YYYY-MM-DD).
    """
    from backend.app.tools.doctor_tools import get_available_slots
    return get_available_slots(doctor_id, date_str)


def book_appointment(
    patient_id: int,
    doctor_id: int,
    date_str: str,
    time_str: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transaction-safe booking tool. Reserves an appointment slot for a patient with a doctor.
    """
    db = SessionLocal()
    try:
        try:
            appt_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return {"status": "error", "message": f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."}

        try:
            parts = time_str.split(":")
            appt_time = datetime.time(int(parts[0]), int(parts[1]))
        except Exception:
            return {"status": "error", "message": f"Invalid time format '{time_str}'. Expected HH:MM."}

        result = AppointmentService.book_appointment(
            db=db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            reason_for_visit=reason
        )
        return {"status": "success", "booking": result}

    except SlotConflictError as e:
        return {"status": "conflict", "message": str(e)}
    except InvalidOperationError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during booking: {str(e)}"}
    finally:
        db.close()


def cancel_appointment(appointment_id: int, patient_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Cancel an existing booked appointment.
    """
    db = SessionLocal()
    try:
        result = AppointmentService.cancel_appointment(db, appointment_id, patient_id)
        return {"status": "success", "result": result}
    except AppointmentNotFoundError as e:
        return {"status": "error", "message": str(e)}
    except InvalidOperationError as e:
        return {"status": "unauthorized", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def reschedule_appointment(
    appointment_id: int,
    new_date_str: str,
    new_time_str: str,
    patient_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Reschedule an existing appointment to a new date and time.
    """
    db = SessionLocal()
    try:
        try:
            new_date = datetime.date.fromisoformat(new_date_str)
            parts = new_time_str.split(":")
            new_time = datetime.time(int(parts[0]), int(parts[1]))
        except Exception:
            return {"status": "error", "message": "Invalid date or time format. Expected YYYY-MM-DD and HH:MM."}

        result = AppointmentService.reschedule_appointment(db, appointment_id, new_date, new_time, patient_id)
        return {"status": "success", "result": result}
    except (SlotConflictError, AppointmentNotFoundError, InvalidOperationError) as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
