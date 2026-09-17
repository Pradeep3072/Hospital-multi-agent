import datetime
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models import Patient, Appointment, MedicalRecord, Prescription
from backend.app.services.audit_service import AuditService


class PatientService:
    @staticmethod
    def get_patient_by_id(db: Session, patient_id: int) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.id == patient_id).first()

    @staticmethod
    def list_all_patients(db: Session) -> List[Dict[str, Any]]:
        patients = db.query(Patient).all()
        return [
            {
                "id": p.id,
                "name": p.full_name,
                "email": p.email or "",
                "phone": p.phone_number or "",
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
        
        AuditService.log_action(db, action="READ_PROFILE", resource="Patient", details=f"Patient ID: {patient_id}", patient_id=patient_id)

        return {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone_number,
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

        AuditService.log_action(db, action="READ_APPOINTMENTS", resource="Appointment", details=f"Patient ID: {patient_id}", patient_id=patient_id)

        appointments = (
            db.query(Appointment)
            .options(joinedload(Appointment.doctor))
            .filter(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
            .all()
        )

        res = []
        for a in appointments:
            doc_name = a.doctor.full_name if a.doctor else f"Doctor {a.doctor_id}"
            dept = a.doctor.department if a.doctor else None
            spec = a.doctor.specialization if a.doctor else None
            res.append({
                "id": a.id,
                "doctor_id": a.doctor_id,
                "doctor_name": doc_name,
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

    @staticmethod
    def create_patient(
        db: Session,
        name: str,
        date_of_birth: Optional[str] = None,
        gender: Optional[str] = "Female",
        blood_group: Optional[str] = "O+",
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        emergency_contact_name: Optional[str] = None,
        emergency_contact_phone: Optional[str] = None,
        insurance_policy_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new patient record. ID is auto-generated by the database.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Patient name is required.")

        # Parse or default DOB
        if date_of_birth:
            try:
                dob = datetime.date.fromisoformat(date_of_birth)
            except ValueError:
                dob = datetime.date(1995, 1, 1)
        else:
            dob = datetime.date(1995, 1, 1)

        unique_token = uuid.uuid4().hex[:6].upper()
        if not insurance_policy_number or not insurance_policy_number.strip():
            policy_num = f"HC-POL-{unique_token}"
        else:
            policy_num = insurance_policy_number.strip()

        if not email or not email.strip():
            clean_name_parts = "".join(c for c in clean_name if c.isalnum() or c == " ").lower().split()
            prefix = ".".join(clean_name_parts) if clean_name_parts else "patient"
            patient_email = f"{prefix}.{unique_token.lower()}@patient.hopecare.com"
        else:
            patient_email = email.strip()

        new_patient = Patient(
            full_name=clean_name,
            date_of_birth=dob,
            gender=gender or "Other",
            blood_group=blood_group or "O+",
            phone_number=phone_number.strip() if phone_number else f"+1-555-{uuid.uuid4().hex[:4]}",
            email=patient_email,
            address=address.strip() if address else "HopeCare Community Residence",
            emergency_contact_name=emergency_contact_name.strip() if emergency_contact_name else "Next of Kin",
            emergency_contact_phone=emergency_contact_phone.strip() if emergency_contact_phone else "+1-555-0911",
            insurance_policy_number=policy_num
        )

        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)

        AuditService.log_action(db, action="CREATE_PATIENT", resource="Patient", details=f"Created Patient: {clean_name}", patient_id=new_patient.id)

        return {
            "id": new_patient.id,
            "name": new_patient.full_name,
            "date_of_birth": str(new_patient.date_of_birth),
            "gender": new_patient.gender,
            "blood_group": new_patient.blood_group,
            "phone": new_patient.phone_number,
            "email": new_patient.email,
            "policy": new_patient.insurance_policy_number,
            "message": f"Patient {new_patient.full_name} registered successfully with ID #{new_patient.id}"
        }
