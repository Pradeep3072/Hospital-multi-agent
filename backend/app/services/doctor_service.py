import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models import (
    Doctor, User, Department, DoctorSpecialization,
    DoctorSchedule, DoctorLeave, Appointment
)


class DoctorService:
    @staticmethod
    def search_doctors(
        db: Session,
        query: Optional[str] = None,
        specialty: Optional[str] = None,
        department_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        q = db.query(Doctor).options(
            joinedload(Doctor.user),
            joinedload(Doctor.department),
            joinedload(Doctor.specialization)
        )

        if specialty:
            q = q.join(Doctor.specialization).filter(DoctorSpecialization.name.ilike(f"%{specialty}%"))
        
        if department_name:
            q = q.join(Doctor.department).filter(Department.name.ilike(f"%{department_name}%"))

        doctors = q.all()
        results = []
        for d in doctors:
            if not d.user or not d.user.is_active:
                continue

            doc_name = d.user.full_name
            dept_name = d.department.name if d.department else "General"
            spec_name = d.specialization.name if d.specialization else "General"

            # If user query provided, filter across name, dept, spec, bio
            if query:
                combined_text = f"{doc_name} {dept_name} {spec_name} {d.bio or ''}".lower()
                if query.lower() not in combined_text:
                    continue

            results.append({
                "id": d.id,
                "name": doc_name,
                "department": dept_name,
                "specialization": spec_name,
                "consultation_fee": d.consultation_fee,
                "experience_years": d.experience_years,
                "bio": d.bio,
                "email": d.user.email,
                "phone": d.user.phone_number
            })
        return results

    @staticmethod
    def get_doctor_details(db: Session, doctor_id: int) -> Optional[Dict[str, Any]]:
        d = db.query(Doctor).options(
            joinedload(Doctor.user),
            joinedload(Doctor.department),
            joinedload(Doctor.specialization),
            joinedload(Doctor.schedules),
            joinedload(Doctor.leaves)
        ).filter(Doctor.id == doctor_id).first()

        if not d:
            return None

        schedules = [
            {
                "day_of_week": s.day_of_week,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "slot_duration_minutes": s.slot_duration_minutes,
                "is_available": s.is_available
            }
            for s in d.schedules
        ]

        leaves = [
            {
                "leave_date": str(l.leave_date),
                "reason": l.reason
            }
            for l in d.leaves
        ]

        return {
            "id": d.id,
            "name": d.user.full_name,
            "department": d.department.name if d.department else "General",
            "specialization": d.specialization.name if d.specialization else "General",
            "consultation_fee": d.consultation_fee,
            "experience_years": d.experience_years,
            "license_number": d.license_number,
            "bio": d.bio,
            "schedules": schedules,
            "leaves": leaves
        }

    @staticmethod
    def get_available_slots(db: Session, doctor_id: int, target_date: datetime.date) -> List[str]:
        """
        Calculate available time slots for a doctor on a specific date,
        accounting for day of week schedule, approved doctor leaves,
        and existing booked appointments.
        """
        # 1. Check if doctor is on leave
        leave = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_id == doctor_id,
            DoctorLeave.leave_date == target_date
        ).first()
        if leave:
            return []

        # 2. Find schedule for that day of week (0=Mon ... 6=Sun)
        day_of_week = target_date.weekday()
        schedule = db.query(DoctorSchedule).filter(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.day_of_week == day_of_week,
            DoctorSchedule.is_available == True
        ).first()

        if not schedule:
            return []

        # 3. Generate candidate slots
        candidate_slots = []
        current_dt = datetime.datetime.combine(target_date, schedule.start_time)
        end_dt = datetime.datetime.combine(target_date, schedule.end_time)
        delta = datetime.timedelta(minutes=schedule.slot_duration_minutes)

        while current_dt + delta <= end_dt:
            candidate_slots.append(current_dt.time())
            current_dt += delta

        # 4. Filter out already booked slots
        booked_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == target_date,
            Appointment.status.in_(["CONFIRMED", "PENDING"])
        ).all()

        booked_times = {a.appointment_time for a in booked_appointments}
        available_slots = [
            slot.strftime("%H:%M") for slot in candidate_slots if slot not in booked_times
        ]

        return available_slots
