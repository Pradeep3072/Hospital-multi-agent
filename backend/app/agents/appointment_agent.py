import json
import re
import datetime
from typing import Dict, Any, Optional
from google.adk import Agent
from backend.app.tools.appointment_tools import (
    book_appointment, cancel_appointment, reschedule_appointment, check_availability
)
from backend.app.tools.doctor_tools import search_doctors, get_doctor_details
from backend.app.config import settings


# Google ADK Tools for Appointment Agent
def book_appointment_tool(
    patient_id: int,
    doctor_id: int,
    date_str: str,
    time_str: str,
    reason: str = "Consultation"
) -> Dict[str, Any]:
    """
    Transaction-safe booking tool. Books an appointment slot for a patient with a doctor.
    
    Args:
        patient_id: The ID of the patient booking the appointment.
        doctor_id: The ID of the doctor (e.g. 1 for Dr. Mitchell, 4 for Dr. Wilson).
        date_str: The booking date in YYYY-MM-DD format (e.g. 2026-04-10).
        time_str: The booking time in HH:MM format (e.g. 09:00, 10:30).
        reason: The reason for visit or consultation topic.
    """
    return book_appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        date_str=date_str,
        time_str=time_str,
        reason=reason
    )


def cancel_appointment_tool(appointment_id: int, patient_id: int = 1) -> Dict[str, Any]:
    """
    Cancels an existing patient appointment by its appointment ID.
    
    Args:
        appointment_id: Numeric ID of the appointment to cancel.
        patient_id: ID of the patient requesting cancellation.
    """
    return cancel_appointment(appointment_id=appointment_id, patient_id=patient_id)


def reschedule_appointment_tool(
    appointment_id: int,
    new_date_str: str,
    new_time_str: str,
    patient_id: int = 1
) -> Dict[str, Any]:
    """
    Reschedules an existing appointment to a new date and time slot.
    
    Args:
        appointment_id: Numeric ID of the appointment to reschedule.
        new_date_str: The new appointment date in YYYY-MM-DD format.
        new_time_str: The new appointment time in HH:MM format.
        patient_id: ID of the patient.
    """
    return reschedule_appointment(
        appointment_id=appointment_id,
        new_date_str=new_date_str,
        new_time_str=new_time_str,
        patient_id=patient_id
    )


def check_availability_tool(doctor_id: int, date_str: str) -> Dict[str, Any]:
    """
    Checks the available appointment slots for a doctor on a specific date.
    
    Args:
        doctor_id: The numeric ID of the doctor.
        date_str: Date in YYYY-MM-DD format.
    """
    return check_availability(doctor_id=doctor_id, date_str=date_str)


# Google ADK Appointment Agent
appointment_agent = Agent(
    name="appointment_agent",
    model=settings.GEMINI_MODEL,
    description="Executes transaction-safe appointment bookings, cancellations, and reschedulings.",
    instruction=(
        "You are the Appointment Booking Agent for HopeCare General Hospital. "
        "You execute transaction-safe appointment operations using your provided tools: "
        "book_appointment_tool, cancel_appointment_tool, reschedule_appointment_tool, and check_availability_tool. "
        "When confirming a booking, clearly summarize the appointment ID, doctor, date, time, and reason."
    ),
    tools=[
        book_appointment_tool,
        cancel_appointment_tool,
        reschedule_appointment_tool,
        check_availability_tool
    ]
)


class AppointmentAgent:
    name = "Appointment Agent"
    description = "Executes transaction-safe appointment bookings, cancellations, and reschedulings."
    adk_agent = appointment_agent

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = context.get("patient_id", 1)
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        # 1. Check for Cancellation Intent
        cancel_match = re.search(r"\b(cancel)\b.*?(?:appointment\s*#?|#)?(\d+)", msg_lower)
        if cancel_match:
            appt_id = int(cancel_match.group(2))
            tools_called.append("cancel_appointment")
            tool_results["cancellation"] = cancel_appointment(appt_id, patient_id=patient_id)
            res = tool_results["cancellation"]
            if res.get("status") == "success":
                msg = f"✅ **Appointment #{appt_id} Successfully Cancelled**.\n\nA confirmation notice has been sent to your email."
            else:
                msg = f"❌ **Unable to Cancel Appointment**: {res.get('message')}"
            return {
                "agent": self.name,
                "tools_called": tools_called,
                "tool_results": tool_results,
                "response": msg
            }

        # 2. Check for Reschedule Intent
        reschedule_match = re.search(r"\b(reschedule)\b.*?(?:appointment\s*#?|#)?(\d+)", msg_lower)
        date_match = re.search(r"\b(202\d-\d{2}-\d{2})\b", message)
        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", message)

        if reschedule_match and date_match and time_match:
            appt_id = int(reschedule_match.group(2))
            new_date = date_match.group(1)
            new_time = time_match.group(1)
            if len(new_time.split(":")[0]) == 1:
                new_time = f"0{new_time}"

            tools_called.append("reschedule_appointment")
            tool_results["reschedule"] = reschedule_appointment(
                appointment_id=appt_id,
                new_date_str=new_date,
                new_time_str=new_time,
                patient_id=patient_id
            )
            res = tool_results["reschedule"]
            if res.get("status") == "success":
                msg = f"✅ **Appointment #{appt_id} Rescheduled** to **{new_date}** at **{new_time}**."
            else:
                msg = f"❌ **Could not reschedule**: {res.get('message')}"
            return {
                "agent": self.name,
                "tools_called": tools_called,
                "tool_results": tool_results,
                "response": msg
            }

        # 3. Check for Booking Intent
        if any(w in msg_lower for w in ["book", "bok", "schedule", "reserve", "appointment", "consultation", "slot", "slots"]):
            specialty = None
            for spec in ["cardiology", "cardiologist", "cardio", "neurology", "neurologist", "neuro", "pediatrics", "pediatrician", "pedia", "orthopedics", "orthopedic", "ortho", "general medicine", "internal medicine", "physician"]:
                if spec in msg_lower:
                    specialty = spec
                    break

            doc_id = None
            doc_match = re.search(r"(?:doctor\s*|dr\.?\s*)#?(\d+)", msg_lower)
            if doc_match:
                doc_id = int(doc_match.group(1))
            else:
                for name_sub, d_id in [("mitchell", 1), ("chen", 2), ("vance", 3), ("wilson", 4), ("patel", 5)]:
                    if name_sub in msg_lower:
                        doc_id = d_id
                        break

            target_date = None
            if date_match:
                target_date = date_match.group(1)
            elif "tomorrow" in msg_lower:
                target_date = str(datetime.date.today() + datetime.timedelta(days=1))
            
            target_time = None
            if time_match:
                target_time = time_match.group(1)
                if len(target_time.split(":")[0]) == 1:
                    target_time = f"0{target_time}"

            if doc_id and target_date and target_time:
                tools_called.append("book_appointment")
                reason = "Consultation"
                if "reason" in msg_lower:
                    reason = message.split("reason")[-1].strip(": ")
                
                tool_results["booking"] = book_appointment(
                    patient_id=patient_id,
                    doctor_id=doc_id,
                    date_str=target_date,
                    time_str=target_time,
                    reason=reason
                )

                res = tool_results["booking"]
                if res.get("status") == "success":
                    b = res["booking"]
                    msg = (
                        f"🎉 **Appointment Successfully Confirmed!**\n\n"
                        f"- **Appointment ID**: `#{b['appointment_id']}`\n"
                        f"- **Doctor**: {b['doctor_name']}\n"
                        f"- **Date**: {b['date']}\n"
                        f"- **Time**: {b['time']}\n"
                        f"- **Reason**: {b['reason_for_visit']}\n\n"
                        f"✉️ A confirmation email and notification have been dispatched."
                    )
                elif res.get("status") == "conflict":
                    msg = f"⚠️ **Slot Unavailable**: {res.get('message')}\nWould you like me to check other available slots for Dr. #{doc_id} on {target_date}?"
                else:
                    msg = f"❌ **Booking Failed**: {res.get('message')}"

                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }

            # Doctor specified, but no time yet: Check availability
            if doc_id:
                t_date = target_date or str(datetime.date.today() + datetime.timedelta(days=1))
                tools_called.append("check_availability")
                tool_results["availability"] = check_availability(doc_id, t_date)
                slots = tool_results["availability"].get("slots", [])
                
                if slots:
                    slot_txt = ", ".join([f"`{s}`" for s in slots[:6]])
                    msg = (
                        f"📅 **Available slots for Dr. #{doc_id} on {t_date}**:\n\n"
                        f"{slot_txt}\n\n"
                        f"Reply with your chosen time (e.g. *Book Dr. {doc_id} on {t_date} at {slots[0]}*) to confirm your reservation."
                    )
                else:
                    msg = f"No open slots found for Dr. #{doc_id} on {t_date}. Please select another date or doctor."
                
                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }

            # If specialty is mentioned, search doctors
            if specialty:
                tools_called.append("search_doctors")
                tool_results["doctors"] = search_doctors(specialty=specialty)
                docs = tool_results["doctors"].get("doctors", [])
                if docs:
                    doc_list = "\n".join([f"- **Dr. {d['name']}** ({d['specialization']}) — Fee: ${d['consultation_fee']:.2f} (ID: #{d['doctor_id']})" for d in docs])
                    msg = (
                        f"Here are our available {specialty.capitalize()} specialists:\n\n{doc_list}\n\n"
                        f"Which doctor and date would you prefer?"
                    )
                else:
                    msg = f"We couldn't find an available specialist in {specialty}. Please contact hospital reception."
                
                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": (
                "I can help you schedule, reschedule, or cancel your appointment.\n"
                "Please tell me the doctor's name or specialty, preferred date (YYYY-MM-DD), and time."
            )
        }
