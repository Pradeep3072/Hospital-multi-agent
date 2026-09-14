from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models import Patient, User, Appointment, MedicalRecord, Prescription
from backend.app.services.audit_service import AuditService


class PatientService:
    @staticmethod
    def get_patient_by_id(db: Session, patient_id: int) -> Optional[Patient]:
        return db.query(Patient).options(joinedload(Patient.user)).filter(Patient.id == patient_id).first()

    @staticmethod
    def list_all_patients(db: Session) -> List[Dict[str, Any]]:
        patients = db.query(Patient).options(joinedload(Patient.user)).all()
        return [
            {
                "id": p.id,
                "name": p.user.full_name if p.user else f"Patient {p.id}",
                "email": p.user.email if p.user else "",
                "phone": p.user.phone_number if p.user else "",
                "dob": str(p.date_of_birth),
                "gender": p.gender,
                "blood_group": p.blood_group,
                "policy": p.insurance_policy_number
            }
            for p in patients
        ]

    @staticmethod
    def get_patient_profile(db: Session, patient_id: int) -> Optional[Dict[str, Any]]:
        p = PatientService.get_patient_by_id(db, patient_id)
        if not p:
            return None
        
        AuditService.log_action(db, action="READ_PROFILE", resource="Patient", details=f"Patient ID: {patient_id}", user_id=p.user_id)

        return {
            "id": p.id,
            "user_id": p.user_id,
            "full_name": p.user.full_name,
            "email": p.user.email,
            "phone": p.user.phone_number,
            "date_of_birth": str(p.date_of_birth),
            "gender": p.gender,
            "blood_group": p.blood_group,
            "emergency_contact_name": p.emergency_contact_name,
            "emergency_contact_phone": p.emergency_contact_phone,
            "address": p.address,
            "insurance_policy_number": p.insurance_policy_number
        }

    @staticmethod
    def get_patient_appointments(db: Session, patient_id: int) -> List[Dict[str, Any]]:
        p = PatientService.get_patient_by_id(db, patient_id)
        if not p:
            return []

        AuditService.log_action(db, action="READ_APPOINTMENTS", resource="Appointment", details=f"Patient ID: {patient_id}", user_id=p.user_id)

        appointments = (
            db.query(Appointment)
            .options(joinedload(Appointment.doctor))
            .filter(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
            .all()
        )

        res = []
        for a in appointments:
            doc_user = a.doctor.user if a.doctor else None
            dept = a.doctor.department if a.doctor else None
            spec = a.doctor.specialization if a.doctor else None
            res.append({
                "id": a.id,
                "doctor_id": a.doctor_id,
                "doctor_name": doc_user.full_name if doc_user else f"Doctor {a.doctor_id}",
                "department": dept.name if dept else "General",
                "specialization": spec.name if spec else "General",
                "appointment_date": str(a.appointment_date),
                "appointment_time": str(a.appointment_time),
                "status": a.status,
                "reason_for_visit": a.reason_for_visit,
                "notes": a.notes
            })
        return res

    @staticmethod
    def get_patient_records(db: Session, patient_id: int) -> List[Dict[str, Any]]:
        records = (
            db.query(MedicalRecord)
            .filter(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.record_date.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "doctor_name": r.doctor_name,
                "diagnosis": r.diagnosis,
                "treatment_summary": r.treatment_summary,
                "record_date": str(r.record_date)
            }
            for r in records
        ]

    @staticmethod
    def get_patient_prescriptions(db: Session, patient_id: int) -> List[Dict[str, Any]]:
        prescriptions = (
            db.query(Prescription)
            .filter(Prescription.patient_id == patient_id)
            .order_by(Prescription.start_date.desc())
            .all()
        )
        return [
            {
                "id": rx.id,
                "medication_name": rx.medication_name,
                "dosage": rx.dosage,
                "frequency": rx.frequency,
                "start_date": str(rx.start_date),
                "end_date": str(rx.end_date) if rx.end_date else "Ongoing",
                "prescribed_by": rx.prescribed_by
            }
            for rx in prescriptions
        ]
