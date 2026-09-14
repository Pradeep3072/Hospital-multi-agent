import datetime
import threading
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.seed import seed_database
from backend.app.database.models import Appointment
from backend.app.services.appointment_service import AppointmentService, SlotConflictError


def test_appointment_concurrency_race_condition():
    init_db()
    seed_database()

    # Pick a test date and clean any prior test record
    target_date = datetime.date(2026, 11, 4)
    target_time = datetime.time(14, 0)
    doctor_id = 1
    patient_1 = 1
    patient_2 = 2

    # Clean up any leftover test appointment
    cleanup_db = SessionLocal()
    cleanup_db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == target_time
    ).delete()
    cleanup_db.commit()
    cleanup_db.close()

    results = []
    errors = []

    def try_booking(p_id):
        db = SessionLocal()
        try:
            res = AppointmentService.book_appointment(
                db=db,
                patient_id=p_id,
                doctor_id=doctor_id,
                appointment_date=target_date,
                appointment_time=target_time,
                reason_for_visit="Concurrent race test"
            )
            results.append((p_id, res))
        except SlotConflictError as e:
            errors.append((p_id, str(e)))
        finally:
            db.close()

    t1 = threading.Thread(target=try_booking, args=(patient_1,))
    t2 = threading.Thread(target=try_booking, args=(patient_2,))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Exactly one booking must succeed and the other must be rejected
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 slot conflict error, got {len(errors)}"
    assert "Slot" in errors[0][1] or "Race" in errors[0][1] or "not available" in errors[0][1]
