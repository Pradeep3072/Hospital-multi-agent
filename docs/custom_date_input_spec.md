# 📅 Custom Date Input Specification & Required Data

This document details all data fields, formats, validation rules, API contracts, and database constraints needed when accepting a **custom date input** across the Hospital Multi-Agent AI system.

---

## 📌 Executive Summary

A custom date input is utilized across three core operations:
1. **Doctor Availability & Slot Generation**: Querying available consultation slots for a chosen doctor on a specific calendar date.
2. **Appointment Booking & Rescheduling**: Committing a reserved appointment slot with transaction isolation and double-booking conflict locks.
3. **Appointment Filtering & Calendar Views**: Filtering historical and upcoming patient visits within date ranges.

---

## 📋 1. Required Data Fields by Use Case

### Use Case A: Doctor Slot Availability Query
When a patient or staff member selects a custom date to view available time slots:

| Field Name | Type | Required? | Format / Example | Description |
|---|---|---|---|---|
| `doctor_id` | `integer` | **Yes** | `1`, `4` | Unique ID of the physician. |
| `date` | `string` | **Yes** | `2026-09-17` (`YYYY-MM-DD`) | Target consultation date. |

**Endpoint**: `GET /api/v1/doctors/{doctor_id}/slots?date={date}`  
**Expected Response**:
```json
{
  "doctor_id": 1,
  "doctor_name": "Dr. Emily Chen",
  "date": "2026-09-17",
  "day_of_week": "Thursday",
  "total_slots": 8,
  "slots": ["09:00", "09:30", "10:00", "10:30", "14:00", "14:30", "15:00", "15:30"]
}
```

---

### Use Case B: Booking an Appointment
When confirming a reservation with the chosen custom date:

| Field Name | Type | Required? | Format / Example | Description |
|---|---|---|---|---|
| `date` | `string` | **Yes** | `2026-09-17` (`YYYY-MM-DD`) | The selected consultation date. |
| `time` | `string` | **Yes** | `09:30` (`HH:MM`) | The selected slot time (must be one of the doctor's open slots). |
| `doctor_id` | `integer` | **Yes** | `1` | ID of the doctor being booked. |
| `patient_name` | `string` | **Conditional** | `"John Doe"` | Full name of the patient (required if `patient_id` is omitted). |
| `patient_id` | `integer` | **Conditional** | `1` | ID of existing patient (if authenticated/selected). |
| `reason` | `string` | Optional | `"Cardiac checkup & ECG"` | Chief complaint or reason for visit (defaults to `"General Consultation"`). |

**Endpoint**: `POST /api/v1/appointments/book`  
**JSON Payload**:
```json
{
  "doctor_id": 1,
  "date": "2026-09-17",
  "time": "09:30",
  "patient_name": "John Doe",
  "patient_id": 1,
  "reason": "Routine hypertension follow-up"
}
```

---

### Use Case C: Rescheduling an Existing Appointment
When shifting an existing appointment to a new custom date:

| Field Name | Type | Required? | Format / Example | Description |
|---|---|---|---|---|
| `appointment_id` | `integer` | **Yes** (in path) | `101` | ID of the existing confirmed appointment. |
| `new_date` | `string` | **Yes** | `2026-09-24` (`YYYY-MM-DD`) | New appointment date. |
| `new_time` | `string` | **Yes** | `11:00` (`HH:MM`) | New appointment time slot. |
| `patient_id` | `integer` | Optional | `1` | Verifies patient ownership before modification. |

**Endpoint**: `POST /api/v1/appointments/{appointment_id}/reschedule`  
**JSON Payload**:
```json
{
  "patient_id": 1,
  "new_date": "2026-09-24",
  "new_time": "11:00"
}
```

---

### Use Case D: Date Range Filtering (Appointments / Schedules)
When filtering appointments or doctor schedules across a custom date window:

| Field Name | Type | Required? | Format / Example | Description |
|---|---|---|---|---|
| `start_date` | `string` | Optional | `2026-09-01` (`YYYY-MM-DD`) | Window start date. Defaults to current date if omitted. |
| `end_date` | `string` | Optional | `2026-09-30` (`YYYY-MM-DD`) | Window end date. Defaults to `start_date + 30 days`. |
| `status` | `string` | Optional | `"CONFIRMED"` | Filter by `CONFIRMED`, `PENDING`, `CANCELLED`, or `COMPLETED`. |

---

## 🛡️ 2. Validation Rules & Guardrails

When accepting custom date inputs, the system must enforce these validation rules:

### 1. Format & Parsing
- **Standard Format**: `YYYY-MM-DD` (ISO 8601).
- **Regex Guard**: `^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$`
- Must be a valid Gregorian calendar date (e.g. reject `2026-02-30`).

### 2. Temporal Rules
- **Past Dates**: `date >= current_date`  
  *Cannot book or check slots for dates in the past.*
- **Maximum Advance Horizon**: `date <= current_date + 90 days`  
  *Hospital scheduling policy prevents bookings further than 3 months in advance.*
- **Hospital Closures & Public Holidays**: If the date matches a designated hospital closure, system returns an informative holiday alert.

### 3. Physician Operational Rules
- **Weekday Working Schedule**: The day of week `target_date.weekday()` (0 = Monday ... 6 = Sunday) must match an active `DoctorSchedule` row for that doctor where `is_available == True`.
- **Approved Leaves**: The custom date must **not** match any record in `doctor_leaves` for that `doctor_id` where `leave_date == target_date`.
- **Slot Collision**: The combination of `(doctor_id, date, time)` must not exist in `appointments` with status `CONFIRMED` or `PENDING` (enforced by DB unique index `uix_doctor_datetime_slot`).

---

## 💻 3. Implementation Code Snippets

### A. Streamlit UI Date Input Widget
```python
import streamlit as st
import datetime

# Constrain date selection between today and +90 days
min_date = datetime.date.today()
max_date = min_date + datetime.timedelta(days=90)

custom_date = st.date_input(
    label="📅 Select Consultation Date:",
    min_value=min_date,
    max_value=max_date,
    value=min_date + datetime.timedelta(days=1), # default to tomorrow
    help="Choose an upcoming date up to 90 days in advance"
)

# Convert to ISO string for backend consumption
date_str = custom_date.strftime("%Y-%m-%d")
```

### B. FastAPI / Pydantic Schema Validation
```python
from datetime import date
from pydantic import BaseModel, Field, field_validator

class CustomDateQuery(BaseModel):
    doctor_id: int
    date: str = Field(..., description="Target date in YYYY-MM-DD format")

    @field_validator("date")
    @classmethod
    def validate_date_not_in_past(cls, v: str) -> str:
        try:
            parsed_date = date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be formatted as YYYY-MM-DD")
        
        today = date.today()
        if parsed_date < today:
            raise ValueError("Appointment date cannot be in the past")
        if parsed_date > today + datetime.timedelta(days=90):
            raise ValueError("Appointments cannot be booked more than 90 days in advance")
        return v
```

### C. Database Model Columns (SQLAlchemy)
```python
# appointments table
Column("appointment_date", Date, nullable=False, index=True)
Column("appointment_time", Time, nullable=False)

# doctor_leaves table
Column("leave_date", Date, nullable=False, index=True)

# doctor_schedules table
Column("day_of_week", Integer, nullable=False) # 0=Mon ... 6=Sun
Column("start_time", Time, nullable=False)
Column("end_time", Time, nullable=False)
Column("slot_duration_minutes", Integer, default=30)
```

---

## 📊 4. Summary Checklist for Adding Custom Date Input

- [ ] **UI Component**: Add `st.date_input` with `min_value=today` and `max_value=today + 90 days`.
- [ ] **String Serialization**: Convert selected date object to `YYYY-MM-DD` before HTTP requests.
- [ ] **Slot Query Call**: Trigger `GET /api/v1/doctors/{doc_id}/slots?date={date_str}` on date change.
- [ ] **Payload Binding**: Pass `date` and selected `time` into the booking payload for `POST /api/v1/appointments/book`.
- [ ] **Error Handling**: Handle `400 Bad Request` (past date / invalid format) and `409 Conflict` (double-booked slot).
