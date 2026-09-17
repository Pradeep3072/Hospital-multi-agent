import json
import re
import datetime
from typing import Dict, Any, Optional
from google.adk import Agent
from backend.app.tools.doctor_tools import (
    search_doctors,
    get_doctor_details,
    get_available_slots,
    get_available_doctors_by_date
)
from backend.app.config import settings, get_gemini_client


# Google ADK Tools for Doctor Agent
def search_doctors_tool(query: str = "", specialty: str = "") -> Dict[str, Any]:
    """
    Search doctors by physician name, bio keywords, or medical specialization.
    
    Args:
        query: Physician name or free-text query (e.g. 'Mitchell', 'surgery').
        specialty: Medical specialty filter (e.g. 'Cardiology', 'Orthopedics', 'Pediatrics', 'Neurology').
    """
    return search_doctors(query=query if query else None, specialty=specialty if specialty else None)


def get_doctor_details_tool(doctor_id: int) -> Dict[str, Any]:
    """
    Retrieves detailed clinical profile, experience, room number, and consultation fee for a specific doctor.
    
    Args:
        doctor_id: Numeric ID of the doctor (e.g. 1, 2, 3, 4).
    """
    return get_doctor_details(doctor_id=doctor_id)


def get_available_slots_tool(doctor_id: int, date_str: str) -> Dict[str, Any]:
    """
    Retrieves available appointment consultation slots for a doctor on a given date.
    
    Args:
        doctor_id: Numeric ID of the doctor.
        date_str: Date in YYYY-MM-DD format (e.g. 2026-04-10).
    """
    return get_available_slots(doctor_id=doctor_id, date_str=date_str)


def get_available_doctors_on_date_tool(date_str: str, specialty: str = "") -> Dict[str, Any]:
    """
    Retrieves all active hospital doctors who have available consultation slots on a specific date,
    along with their open booking slots.

    Args:
        date_str: Target date in YYYY-MM-DD format (e.g. 2026-04-10).
        specialty: Optional medical specialty filter (e.g. 'Cardiology', 'Orthopedics').
    """
    return get_available_doctors_by_date(date_str=date_str, specialty=specialty if specialty else None)


# Google ADK Doctor Agent
doctor_agent = Agent(
    name="doctor_agent",
    model=settings.GEMINI_MODEL,
    description="Discovers doctors by medical specialty, reviews doctor backgrounds, and retrieves consultation availability.",
    instruction=(
        "You are the Doctor Directory & Specialist Finder Agent for HopeCare General Hospital. "
        "Help patients find physicians by medical specialty (Cardiology, Orthopedics, Neurology, Pediatrics, etc.), "
        "look up doctor bios, fees, and retrieve available appointment slots. "
        "When a user asks which doctors are available on a particular date, call get_available_doctors_on_date_tool "
        "to list all available doctors along with their open booking slots."
    ),
    tools=[
        search_doctors_tool,
        get_doctor_details_tool,
        get_available_slots_tool,
        get_available_doctors_on_date_tool
    ]
)



class DoctorAgent:
    name = "Doctor Agent"
    description = "Discovers doctors by medical specialty, reviews doctor backgrounds, and retrieves consultation availability."
    adk_agent = doctor_agent

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        # 1. Parse date if mentioned
        target_date_str = None
        date_match = re.search(r"\b(202\d-\d{2}-\d{2})\b", message)
        if date_match:
            target_date_str = date_match.group(1)
        elif "day after tomorrow" in msg_lower:
            target_date_str = str(datetime.date.today() + datetime.timedelta(days=2))
        elif "tomorrow" in msg_lower:
            target_date_str = str(datetime.date.today() + datetime.timedelta(days=1))
        elif "today" in msg_lower:
            target_date_str = str(datetime.date.today())
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
                    target_date_str = str(today + datetime.timedelta(days=days_ahead))
                    break

        # 2. Check for specific doctor mention
        doc_id_match = re.search(r"\bdoctor\s*(\d+)\b|\bdr\.?\s*(\d+)\b", msg_lower)
        doctor_id = None
        if doc_id_match:
            doctor_id = int(doc_id_match.group(1) or doc_id_match.group(2))
        else:
            for name_sub, d_id in [("mitchell", 1), ("chen", 2), ("vance", 3), ("wilson", 4), ("patel", 5)]:
                if name_sub in msg_lower:
                    doctor_id = d_id
                    break

        # 3. Check for specialty mention
        specialty = None
        for spec in ["cardiologist", "cardiology", "cardio", "neurologist", "neurology", "neuro", "pediatrician", "pediatrics", "pedia", "orthopedic", "orthopedics", "ortho", "internal medicine", "general medicine", "general"]:
            if spec in msg_lower:
                specialty = spec
                break

        # Case A: Specific doctor requested with date
        if doctor_id and target_date_str:
            tools_called.append("get_available_slots")
            slots_res = get_available_slots(doctor_id, target_date_str)
            tool_results["slots"] = slots_res
            tools_called.append("get_doctor_details")
            doc_d = get_doctor_details(doctor_id)
            tool_results["doctor"] = doc_d
            tool_results["target_date"] = target_date_str
            if doc_d.get("doctor"):
                doc_obj = dict(doc_d["doctor"])
                doc_obj["available_slots"] = slots_res.get("slots", [])
                doc_obj["date"] = target_date_str
                tool_results["auto_select_doctor"] = doc_obj
                tool_results["doctors"] = [doc_obj]

        # Case B: Date specified without a specific doctor -> Show all available doctors with booking slots
        elif target_date_str:
            tools_called.append("get_available_doctors_by_date")
            avail_res = get_available_doctors_by_date(date_str=target_date_str, specialty=specialty)
            tool_results["available_doctors_data"] = avail_res
            avail_docs = avail_res.get("doctors", [])
            tool_results["available_doctors"] = avail_docs
            tool_results["doctors"] = avail_docs
            tool_results["target_date"] = target_date_str
            tool_results["day_of_week"] = avail_res.get("day_of_week")
            if len(avail_docs) == 1:
                tool_results["auto_select_doctor"] = avail_docs[0]

        # Case C: General Doctor search by specialty or query
        else:
            tools_called.append("search_doctors")
            tool_results["doctors"] = search_doctors(
                query=None if specialty else message,
                specialty=specialty
            )
            docs = tool_results["doctors"].get("doctors", [])
            if len(docs) == 1:
                tool_results["auto_select_doctor"] = docs[0]

        client = get_gemini_client()
        if client:
            try:
                # Construct compact, low-latency summary for LLM prompt
                summary_data = {}
                if "available_doctors" in tool_results:
                    avail_docs = tool_results["available_doctors"]
                    summary_data["target_date"] = tool_results.get("target_date")
                    summary_data["day_of_week"] = tool_results.get("day_of_week")
                    summary_data["available_specialists"] = [
                        {
                            "name": d["name"],
                            "specialty": d.get("specialization"),
                            "fee": f"${d.get('consultation_fee', 100):.0f}",
                            "open_slots_count": len(d.get("available_slots", [])),
                            "open_slots_sample": d.get("available_slots", [])[:6]
                        }
                        for d in avail_docs[:5]
                    ]
                elif "slots" in tool_results:
                    summary_data["doctor"] = tool_results.get("doctor", {}).get("doctor", {}).get("name")
                    summary_data["date"] = tool_results.get("target_date")
                    summary_data["open_slots"] = tool_results.get("slots", {}).get("slots", [])[:8]
                elif "doctors" in tool_results:
                    doc_list = tool_results["doctors"].get("doctors", []) if isinstance(tool_results["doctors"], dict) else tool_results["doctors"]
                    summary_data["physicians"] = [
                        {
                            "name": d["name"],
                            "specialty": d.get("specialization"),
                            "fee": f"${d.get('consultation_fee', 100):.0f}",
                            "experience": f"{d.get('experience_years', 5)} yrs"
                        }
                        for d in doc_list[:5]
                    ]

                prompt = (
                    f"You are the Doctor Specialist Agent for HopeCare General Hospital.\n"
                    f"Physician Findings:\n{json.dumps(summary_data, indent=2)}\n\n"
                    f"User Query: {message}\n"
                    f"Provide a warm, scannable recommendation (under 120 words) detailing physician names, specialties, "
                    f"and available booking slots. Inform the user they can click 'Book Slot' on any physician card below or reply to confirm."
                )
                response = client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                return {
                    "agent": self.name,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                    "response": response.text
                }
            except Exception:
                pass


        # Deterministic formatting fallback
        output = []
        if "available_doctors" in tool_results:
            avail_docs = tool_results["available_doctors"]
            t_date = tool_results.get("target_date", "")
            dow = tool_results.get("day_of_week", "")
            date_display = f"{t_date} ({dow})" if dow else t_date
            spec_title = f" ({specialty.capitalize()})" if specialty else ""
            if avail_docs:
                output.append(f"### 🗓️ Available Doctors on {date_display}{spec_title}\n")
                output.append("The following physicians have open consultation slots available:\n")
                for d in avail_docs:
                    slots = d.get("available_slots", [])
                    slot_txt = ", ".join([f"`{s}`" for s in slots[:8]])
                    if len(slots) > 8:
                        slot_txt += f" *(+{len(slots)-8} more)*"
                    fee = f"${d.get('consultation_fee', 100):.0f}"
                    output.append(
                        f"- **Dr. {d['name']}** — *{d.get('specialization', 'General')}* (Fee: {fee})\n"
                        f"  - **Available Booking Slots**: {slot_txt}\n"
                    )
                output.append("\n👉 Reply with *Book appointment with Dr. [Name] at [Time]* or click **Select & Book** below to reserve your slot.")
            else:
                output.append(f"No available doctors or open slots found on **{date_display}**{spec_title}. Please select another date or specialty.")

        elif "slots" in tool_results:
            slots_data = tool_results["slots"]
            doc_name = tool_results.get("doctor", {}).get("doctor", {}).get("name", f"Doctor #{slots_data.get('doctor_id')}")
            slots = slots_data.get("slots", [])
            if slots:
                slot_txt = ", ".join([f"`{s}`" for s in slots[:8]])
                output.append(
                    f"### Available Consultation Slots\n"
                    f"**Doctor**: Dr. {doc_name}\n"
                    f"**Date**: {slots_data.get('date')}\n\n"
                    f"Open slots: {slot_txt}\n\n"
                    f"Would you like to book one of these slots?"
                )
            else:
                output.append(f"No available slots found for Dr. {doc_name} on {slots_data.get('date')}. Please select another date.")

        elif "doctors" in tool_results:
            doc_list = tool_results["doctors"].get("doctors", []) if isinstance(tool_results["doctors"], dict) else tool_results["doctors"]
            if doc_list:
                output.append("### Recommended Specialists\n")
                for d in doc_list:
                    room = f" | **Room**: {d['room_number']}" if d.get('room_number') else ""
                    output.append(
                        f"- **Dr. {d.get('name', 'Specialist')}** — *{d.get('specialization', 'General')}*\n"
                        f"  - **Experience**: {d.get('experience_years', 5)} years{room}\n"
                        f"  - **Consultation Fee**: ${d.get('consultation_fee', 100.0):.2f}\n"
                        f"  - **Bio**: {d.get('bio', '')}\n"
                    )
                output.append("Reply with *Book appointment with Dr. [Name]* to schedule your visit.")
            else:
                output.append("No doctors found matching your query. Please try searching for a different specialty like Cardiology, Orthopedics, or Neurology.")

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": "\n".join(output)
        }

