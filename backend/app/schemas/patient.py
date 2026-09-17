from typing import Optional
from pydantic import BaseModel, Field


class CreatePatientRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Patient full name (e.g. Emma Watson)")
    date_of_birth: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD format")
    gender: Optional[str] = Field(default="Female", description="Gender (Male, Female, Other)")
    blood_group: Optional[str] = Field(default="O+", description="Blood group (e.g. O+, A-, B+)")
    phone_number: Optional[str] = Field(default=None, description="Contact phone number")
    email: Optional[str] = Field(default=None, description="Primary email address")
    address: Optional[str] = Field(default=None, description="Residential address")
    emergency_contact_name: Optional[str] = Field(default=None, description="Emergency contact person name")
    emergency_contact_phone: Optional[str] = Field(default=None, description="Emergency contact phone number")
    insurance_policy_number: Optional[str] = Field(default=None, description="Insurance policy or card number")
