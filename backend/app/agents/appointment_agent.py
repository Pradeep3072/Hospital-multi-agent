import json
import re
import datetime
from typing import Dict, Any, Optional
from google.adk import Agent
from backend.app.tools.appointment_tools import (
    book_appointment, cancel_appointment, reschedule_appointment, check_availability
)
from backend.app.tools.doctor_tools import search_doctors, get_doctor_details, get_available_doctors_by_date
from backend.app.config import settings


# Google ADK Tools for Appointment Agent
def get_available_doctors_on_date_tool(date_str: str, specialty: str = "") -> Dict[str, Any]:
    """
    Retrieves all available doctors who have open consultation slots on a specific date (YYYY-MM-DD),
    along with their open booking slots.
    
    Args:
        date_str: Date in YYYY-MM-DD format (e.g. 2026-04-10).
        specialty: Optional medical specialty (e.g. 'Cardiology', 'Orthopedics').
    """
    return get_available_doctors_by_date(date_str=date_str, specialty=specialty if specialty else None)


def search_doctors_tool(query: str = "", specialty: str = "") -> Dict[str, Any]:
    """
    Search doctors by physician name, bio keywords, or medical specialization.
    Use this when a patient mentions a medical specialty to find available doctors.
    
    Args:
        query: Physician name or free-text query.
        specialty: Medical specialty filter (e.g. 'Cardiology', 'Orthopedics', 'Pediatrics', 'Neurology', 'General Medicine').
    """
    return search_doctors(query=query if query else None, specialty=specialty if specialty else None)


def book_appointment_tool(
    patient_id: int,
    doctor_id: int,
    date_str: str,
    time_str: str,
    reason: str = "Consultation"
) -> Dict[str, Any]:
    """
    Transaction-safe booking tool. Finalizes an appointment booking with a doctor.
    CRITICAL: ONLY invoke this tool when the patient has explicitly confirmed ALL THREE parameters:
    doctor_id, date_str, and time_str.
    DO NOT guess, assume, or use default values for any parameters.
    
    Args:
        patient_id: Numeric ID of the authenticated patient.
        doctor_id: Numeric ID of the doctor explicitly chosen by the patient.
        date_str: Booking date in YYYY-MM-DD format explicitly chosen by the patient.
        time_str: Booking time in HH:MM format explicitly selected by the patient from open slots.
        reason: The reason for visit or clinical symptom described by the patient.
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
    Use this to show open consultation slots to the patient so they can choose a time.
    
    Args:
        doctor_id: The numeric ID of the doctor.
        date_str: Date in YYYY-MM-DD format requested by the patient.
    """
    return check_availability(doctor_id=doctor_id, date_str=date_str)


# Google ADK Appointment Agent
appointment_agent = Agent(
    name="appointment_agent",
    model=settings.GEMINI_MODEL,
    description="Manages doctor appointments: slot verification, doctor search, and transaction-safe booking, rescheduling, or cancellation.",
    instruction=(
        "You are the Appointment Scheduling & Booking Agent for HopeCare General Hospital.\n"
        "Your role is to guide patients step-by-step through booking, rescheduling, and cancelling appointments.\n\n"
        "🚨 MANDATORY SAFETY & APPOINTMENT PROTOCOL — STRICT RULES:\n"
        "1. NEVER AUTOMATICALLY BOOK AN APPOINTMENT.\n"
        "   Under NO circumstances should you call `book_appointment_tool` unless the patient has EXPLICITLY confirmed ALL THREE requirements:\n"
        "   - The Doctor (by name or ID)\n"
        "   - The Specific Date (in YYYY-MM-DD format)\n"
        "   - The Specific Time Slot (in HH:MM format, chosen from available open slots)\n\n"
        "2. ZERO ASSUMPTIONS & NO DEFAULT VALUES:\n"
        "   - NEVER assume or default a doctor (do NOT default to Dr. Sarah Mitchell or ID 1).\n"
        "   - NEVER assume or default a date (do NOT pick an arbitrary date unless the user explicitly stated it).\n"
        "   - NEVER assume or default a time slot (do NOT pick 09:00 or any slot without the patient selecting it).\n\n"
        "3. MULTI-STEP CONVERSATIONAL FLOW:\n"
        "   - STEP 1 (Missing Doctor / Specialty):\n"
        "     If the patient says 'book appointment' or does not specify a physician or medical specialty, ask:\n"
        "     'Which doctor or medical specialty (such as Cardiology, Neurology, Pediatrics, Orthopedics, or General Medicine) would you like to see, and on what date?'\n"
        "     If they mention a specialty (e.g. 'Cardiology'), call `search_doctors_tool(specialty=...)` and list the available specialists to let them choose.\n\n"
        "   - STEP 2 (Missing Date):\n"
        "     If the doctor is specified but no date is provided, ask the user what date they would like to visit.\n\n"
        "   - STEP 3 (Show Open Slots):\n"
        "     Once the doctor and date are known, call `check_availability_tool(doctor_id=..., date_str=...)` to retrieve the real open slots.\n"
        "     Display the open slots clearly to the patient (e.g. 09:00, 09:30, 10:00) and ask them to select their preferred time slot.\n\n"
        "   - STEP 4 (Finalize Booking):\n"
        "     ONLY call `book_appointment_tool` after the patient has explicitly selected their preferred time slot from the open slots.\n"
        "     Summarize the booking: Appointment ID, Doctor Name, Date, Time, and Reason for visit.\n\n"
        "4. CANCELLATION & RESCHEDULING:\n"
        "   - For cancellation, require the appointment ID before calling `cancel_appointment_tool`.\n"
        "   - For rescheduling, require the appointment ID, new date, and new time slot before calling `reschedule_appointment_tool`."
    ),
    tools=[
        search_doctors_tool,
        get_available_doctors_on_date_tool,
        check_availability_tool,
        book_appointment_tool,
        cancel_appointment_tool,
        reschedule_appointment_tool
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
            elif "day after tomorrow" in msg_lower:
                target_date = str(datetime.date.today() + datetime.timedelta(days=2))
            elif "tomorrow" in msg_lower:
                target_date = str(datetime.date.today() + datetime.timedelta(days=1))
            elif "today" in msg_lower:
                target_date = str(datetime.date.today())
            else:
                days_map = {
                    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                    "friday": 4, "saturday": 5, "sunday": 6
                }
                for day_name, day_idx in days_map.items():
                    if day_name in msg_lower:
                        today = datetime.date.today()
                        days_ahead = (day_idx - today.weekday()) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                        target_date = str(today + datetime.timedelta(days=days_ahead))
                        break

            target_time = None
            if time_match:
                target_time = time_match.group(1)
                if len(target_time.split(":")[0]) == 1:
                    target_time = f"0{target_time}"

            tool_results["booking_intent"] = {
                "show_booking_widget": True,
                "doctor_id": doc_id,
                "specialty": specialty,
                "target_date": target_date
            }

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

            # If target_date is mentioned without a specific doctor: Show all available doctors with booking slots
            if target_date and not doc_id:
                tools_called.append("get_available_doctors_by_date")
                avail_res = get_available_doctors_by_date(date_str=target_date, specialty=specialty)
                avail_docs = avail_res.get("doctors", [])
                tool_results["available_doctors"] = avail_docs
                tool_results["doctors"] = avail_docs
                tool_results["booking_intent"] = {
                    "show_booking_widget": True,
                    "target_date": target_date,
                    "specialty": specialty
                }
                
                day_name = avail_res.get("day_of_week", "")
                date_label = f"{target_date} ({day_name})" if day_name else target_date
                spec_label = f" {specialty.capitalize()}" if specialty else ""

                if avail_docs:
                    doc_lines = []
                    for d in avail_docs:
                        slots = d.get("available_slots", [])
                        slot_txt = ", ".join([f"`{s}`" for s in slots[:8]])
                        if len(slots) > 8:
                            slot_txt += f" *(+{len(slots)-8} more)*"
                        doc_lines.append(
                            f"- **Dr. {d['name']}** — *{d.get('specialization', 'General')}* (Fee: ${d.get('consultation_fee', 100):.0f})\n"
                            f"  🕒 **Available Slots**: {slot_txt}"
                        )
                    docs_text = "\n".join(doc_lines)
                    msg = (
                        f"### 🗓️ Available Doctors on {date_label}{spec_label}\n\n"
                        f"{docs_text}\n\n"
                        f"👉 Which doctor or time slot would you like to book? "
                        f"You can choose in the booking drawer below or reply with *Book Dr. [Name] on {target_date} at [Time]*."
                    )
                else:
                    msg = f"No available doctors or open slots were found on **{date_label}**{spec_label}. Please select another date or specialty."

                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": msg
                }

            # If specialty is mentioned without a date, search doctors
            if specialty:
                tools_called.append("search_doctors")
                tool_results["doctors"] = search_doctors(specialty=specialty)
                docs = tool_results["doctors"].get("doctors", [])
                if docs:
                    seen_names = set()
                    doc_lines = []
                    for d in docs:
                        dname = d['name'] if str(d['name']).startswith('Dr.') else f"Dr. {d['name']}"
                        if dname in seen_names:
                            continue
                        seen_names.add(dname)
                        did = d.get('id', d.get('doctor_id', ''))
                        fee = d.get('consultation_fee', 100)
                        spec = d.get('specialization', specialty.capitalize())
                        doc_lines.append(f"- **{dname}** ({spec}) — Fee: ${fee:.2f} (ID: #{did})")
                        if len(doc_lines) >= 5:
                            break
                    doc_list = "\n".join(doc_lines)
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
                    "I would be glad to help you schedule an appointment! "
                    "Could you please let me know:\n\n"
                    "1. **Doctor or Medical Specialty** (e.g. Cardiology, General Medicine, Pediatrics, etc.)\n"
                    "2. **Preferred Date** (e.g. tomorrow or YYYY-MM-DD)\n\n"
                    "Once you share that, I will check real-time availability and let you pick your preferred time slot."
                )
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
