from typing import Optional
from pydantic import BaseModel, Field


class BookAppointmentRequest(BaseModel):
    patient_id: int = Field(..., description="ID of the patient booking the appointment")
    doctor_id: int = Field(..., description="ID of the doctor")
    date: str = Field(..., description="Appointment date in YYYY-MM-DD format")
    time: str = Field(..., description="Appointment slot time in HH:MM format")
    reason: Optional[str] = Field(default="General Consultation", description="Reason for consultation")


class RescheduleAppointmentRequest(BaseModel):
    patient_id: Optional[int] = None
    new_date: str = Field(..., description="New appointment date in YYYY-MM-DD format")
    new_time: str = Field(..., description="New appointment slot time in HH:MM format")


class CancelAppointmentRequest(BaseModel):
    patient_id: Optional[int] = None
