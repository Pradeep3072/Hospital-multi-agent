from typing import Optional
from pydantic import BaseModel, Field


class CreateDoctorRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Full name of the doctor (e.g., Dr. Marcus Vance)")
    department_id: Optional[int] = Field(default=None, description="Department ID")
    department_name: Optional[str] = Field(default=None, description="Department name (e.g., Cardiology)")
