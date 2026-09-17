import datetime
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from backend.app.database.models import (
    Doctor, Department, DoctorSpecialization,
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
            joinedload(Doctor.department),
            joinedload(Doctor.specialization)
        ).join(Doctor.department).join(Doctor.specialization)

        if specialty:
            spec_term = specialty.lower().strip()
            if "cardio" in spec_term:
                q = q.filter(or_(DoctorSpecialization.name.ilike("%cardio%"), Department.name.ilike("%cardio%")))
            elif "neuro" in spec_term:
                q = q.filter(or_(DoctorSpecialization.name.ilike("%neuro%"), Department.name.ilike("%neuro%")))
            elif "pedia" in spec_term:
                q = q.filter(or_(DoctorSpecialization.name.ilike("%pedia%"), Department.name.ilike("%pedia%")))
            elif "ortho" in spec_term:
                q = q.filter(or_(DoctorSpecialization.name.ilike("%ortho%"), Department.name.ilike("%ortho%")))
            elif "general" in spec_term or "internal" in spec_term:
                q = q.filter(or_(DoctorSpecialization.name.ilike("%internal%"), Department.name.ilike("%general%")))
            else:
                q = q.filter(or_(DoctorSpecialization.name.ilike(f"%{spec_term}%"), Department.name.ilike(f"%{spec_term}%")))
        
        if department_name:
            q = q.filter(Department.name.ilike(f"%{department_name}%"))

        doctors = q.all()
        results = []
        for d in doctors:
            if not d.is_active:
                continue

            doc_name = d.full_name
            dept_name = d.department.name if d.department else "General"
            spec_name = d.specialization.name if d.specialization else "General"

            # If user query provided, filter across name, dept, spec, bio
            if query:
                combined_text = f"{doc_name} {dept_name} {spec_name} {d.bio or ''}".lower()
                q_words = [w for w in query.lower().split() if len(w) > 2 and w not in ["book", "appointment", "find", "show", "the", "with", "for"]]
                if q_words:
                    if not any(w in combined_text for w in q_words):
                        continue
                elif query.lower() not in combined_text:
                    continue

            results.append({
                "id": d.id,
                "name": doc_name,
                "department": dept_name,
                "specialization": spec_name,
                "consultation_fee": d.consultation_fee,
                "experience_years": d.experience_years,
                "bio": d.bio,
                "email": d.email,
                "phone": d.phone_number
            })
        return results

    @staticmethod
    def get_doctor_details(db: Session, doctor_id: int) -> Optional[Dict[str, Any]]:
        d = db.query(Doctor).options(
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
            "name": d.full_name,
            "department": d.department.name if d.department else "General",
            "specialization": d.specialization.name if d.specialization else "General",
            "consultation_fee": d.consultation_fee,
            "experience_years": d.experience_years,
            "license_number": d.license_number,
            "bio": d.bio,
            "schedules": schedules,
            "leaves": leaves,
            "email": d.email,
            "phone": d.phone_number
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

    @staticmethod
    def create_doctor(
        db: Session,
        name: str,
        department_id: Optional[int] = None,
        department_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new doctor record requiring only name and department.
        The doctor ID is auto-generated by the database, and license/schedules are auto-populated.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Doctor name is required.")

        # 1. Resolve department
        dept = None
        if department_id:
            dept = db.query(Department).filter(Department.id == department_id).first()
        elif department_name:
            dept = db.query(Department).filter(Department.name.ilike(f"%{department_name.strip()}%")).first()

        if not dept:
            dept = db.query(Department).first()
            if not dept:
                dept = Department(
                    name=department_name or "General Medicine",
                    description="General Healthcare and Outpatient Services"
                )
                db.add(dept)
                db.flush()

        # 2. Resolve specialization
        spec = db.query(DoctorSpecialization).filter(
            or_(
                DoctorSpecialization.name.ilike(f"%{dept.name}%"),
                DoctorSpecialization.description.ilike(f"%{dept.name}%")
            )
        ).first()

        if not spec:
            spec_name = f"{dept.name} Specialist"
            spec = db.query(DoctorSpecialization).filter(DoctorSpecialization.name == spec_name).first()
            if not spec:
                spec = DoctorSpecialization(
                    name=spec_name,
                    description=f"Specialist in {dept.name}"
                )
                db.add(spec)
                db.flush()

        # 3. Auto-generate unique license number and email
        unique_token = uuid.uuid4().hex[:6].upper()
        license_num = f"DOC-{unique_token}"
        clean_name_parts = "".join(c for c in clean_name if c.isalnum() or c == " ").lower().split()
        email_prefix = ".".join(clean_name_parts[-2:]) if len(clean_name_parts) >= 2 else (clean_name_parts[0] if clean_name_parts else "doctor")
        email = f"{email_prefix}.{unique_token.lower()}@hopecare.com"

        # 4. Create Doctor
        new_doc = Doctor(
            full_name=clean_name,
            department_id=dept.id,
            specialization_id=spec.id,
            license_number=license_num,
            consultation_fee=100.0,
            experience_years=5,
            email=email,
            phone_number=f"+1-555-{uuid.uuid4().hex[:4]}",
            bio=f"Board-certified physician in {dept.name} at HopeCare Hospital.",
            is_active=True
        )
        db.add(new_doc)
        db.flush()

        # 5. Automatically create standard weekday schedule (Mon-Fri, 09:00 - 17:00, 30m slots)
        start_t = datetime.time(9, 0)
        end_t = datetime.time(17, 0)
        for day in range(5):
            sched = DoctorSchedule(
                doctor_id=new_doc.id,
                day_of_week=day,
                start_time=start_t,
                end_time=end_t,
                slot_duration_minutes=30,
                is_available=True
            )
            db.add(sched)

        db.commit()
        db.refresh(new_doc)

        return {
            "id": new_doc.id,
            "name": new_doc.full_name,
            "department": dept.name,
            "department_id": dept.id,
            "specialization": spec.name,
            "license_number": new_doc.license_number,
            "consultation_fee": new_doc.consultation_fee,
            "experience_years": new_doc.experience_years,
            "email": new_doc.email,
            "message": f"Doctor {new_doc.full_name} created successfully with ID #{new_doc.id}"
        }
