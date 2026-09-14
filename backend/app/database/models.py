import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Time,
    ForeignKey, Float, UniqueConstraint, Enum, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False) # admin, doctor, patient, staff
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    role = relationship("Role", back_populates="users")
    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    location_building = Column(String(100), nullable=True)
    floor = Column(Integer, nullable=True)
    contact_phone = Column(String(30), nullable=True)

    doctors = relationship("Doctor", back_populates="department")
    services = relationship("HospitalService", back_populates="department")


class DoctorSpecialization(Base):
    __tablename__ = "doctor_specializations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    doctors = relationship("Doctor", back_populates="specialization")


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    specialization_id = Column(Integer, ForeignKey("doctor_specializations.id"), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    consultation_fee = Column(Float, default=50.0)
    experience_years = Column(Integer, default=5)
    bio = Column(Text, nullable=True)

    user = relationship("User", back_populates="doctor")
    department = relationship("Department", back_populates="doctors")
    specialization = relationship("DoctorSpecialization", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    leaves = relationship("DoctorLeave", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False) # 0=Monday ... 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, default=30)
    is_available = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="schedules")


class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    leave_date = Column(Date, nullable=False)
    reason = Column(String(255), nullable=True)

    doctor = relationship("Doctor", back_populates="leaves")


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)
    blood_group = Column(String(10), nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    insurance_policy_number = Column(String(100), nullable=True)

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    status = Column(String(30), default="CONFIRMED") # PENDING, CONFIRMED, CANCELLED, COMPLETED
    reason_for_visit = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Concurrency constraint: a doctor cannot have 2 active bookings at the same date & time
    __table_args__ = (
        UniqueConstraint('doctor_id', 'appointment_date', 'appointment_time', name='uix_doctor_datetime_slot'),
    )

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    diagnosis = Column(String(255), nullable=False)
    treatment_summary = Column(Text, nullable=True)
    record_date = Column(Date, default=datetime.date.today)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="medical_records")


class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_name = Column(String(150), nullable=False)
    dosage = Column(String(100), nullable=False) # e.g., 500mg
    frequency = Column(String(100), nullable=False) # e.g., Twice daily after meals
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    prescribed_by = Column(String(100), nullable=False)

    patient = relationship("Patient", back_populates="prescriptions")


class HospitalService(Base):
    __tablename__ = "hospital_services"
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    cost = Column(Float, nullable=True)
    availability_hours = Column(String(100), default="24/7")

    department = relationship("Department", back_populates="services")


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    coverage_type = Column(String(100), default="Comprehensive")
    network_tier = Column(String(50), default="In-Network")
    contact_phone = Column(String(50), nullable=True)
    claims_email = Column(String(100), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String(30), default="email") # email, sms, push
    recipient = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(30), default="SENT") # PENDING, SENT, FAILED
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    summary = Column(Text, nullable=True)

    messages = relationship("MemoryRecord", back_populates="conversation")


class MemoryRecord(Base):
    __tablename__ = "memory_records"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(30), nullable=False) # user, agent, system, tool
    agent_name = Column(String(50), nullable=True) # root, doctor, appointment, etc.
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False) # READ, WRITE, BOOK_APPOINTMENT, CANCEL_APPOINTMENT, etc.
    resource = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
