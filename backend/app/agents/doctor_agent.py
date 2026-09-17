import json
import re
import datetime
from typing import Dict, Any, Optional
from google.adk import Agent
from backend.app.tools.doctor_tools import search_doctors, get_doctor_details, get_available_slots
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


# Google ADK Doctor Agent
doctor_agent = Agent(
    name="doctor_agent",
    model=settings.GEMINI_MODEL,
    description="Discovers doctors by medical specialty, reviews doctor backgrounds, and retrieves consultation availability.",
    instruction=(
        "You are the Doctor Directory & Specialist Finder Agent for HopeCare General Hospital. "
        "Help patients find physicians by medical specialty (Cardiology, Orthopedics, Neurology, Pediatrics, etc.), "
        "look up doctor bios, fees, and retrieve available appointment slots using search_doctors_tool, "
        "get_doctor_details_tool, and get_available_slots_tool."
    ),
    tools=[
        search_doctors_tool,
        get_doctor_details_tool,
        get_available_slots_tool
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

        # 1. Check if user is asking for available slots
        date_match = re.search(r"\b(202\d-\d{2}-\d{2})\b", message)
        doc_id_match = re.search(r"\bdoctor\s*(\d+)\b|\bdr\.?\s*(\d+)\b", msg_lower)
        
        doctor_id = None
        if doc_id_match:
            doctor_id = int(doc_id_match.group(1) or doc_id_match.group(2))
        else:
            for name_sub, d_id in [("mitchell", 1), ("chen", 2), ("vance", 3), ("wilson", 4), ("patel", 5)]:
                if name_sub in msg_lower:
                    doctor_id = d_id
                    break

        specialty = None
        for spec in ["cardiologist", "cardiology", "cardio", "neurologist", "neurology", "neuro", "pediatrician", "pediatrics", "pedia", "orthopedic", "orthopedics", "ortho", "internal medicine", "general medicine", "general"]:
            if spec in msg_lower:
                specialty = spec
                break

        if ("slot" in msg_lower or "availability" in msg_lower or "available" in msg_lower or "free" in msg_lower) and (date_match or "tomorrow" in msg_lower or "today" in msg_lower):
            target_date_str = None
            if date_match:
                target_date_str = date_match.group(1)
            elif "tomorrow" in msg_lower:
                tomorrow = datetime.date.today() + datetime.timedelta(days=1)
                target_date_str = str(tomorrow)
            else:
                target_date_str = str(datetime.date.today())

            target_doc_id = doctor_id or 1
            tools_called.append("get_available_slots")
            tool_results["slots"] = get_available_slots(target_doc_id, target_date_str)
            tools_called.append("get_doctor_details")
            doc_d = get_doctor_details(target_doc_id)
            tool_results["doctor"] = doc_d
            if doc_d.get("doctor"):
                tool_results["auto_select_doctor"] = doc_d["doctor"]
                tool_results["doctors"] = [doc_d["doctor"]]

        else:
            # Doctor search by specialty or query
            tools_called.append("search_doctors")
            tool_results["doctors"] = search_doctors(
                query=None if specialty else message,
                specialty=specialty
            )
            docs = tool_results["doctors"].get("doctors", [])
            if docs:
                tool_results["auto_select_doctor"] = docs[0]

        client = get_gemini_client()
        if client:
            try:
                prompt = (
                    f"You are the Doctor Specialist Agent for HopeCare General Hospital.\n"
                    f"Relevant Physician Data:\n{json.dumps(tool_results, indent=2)}\n\n"
                    f"User Query: {message}\n"
                    f"Provide an informative, welcoming recommendation detailing the doctor's name, specialization, "
                    f"consultation fee, room, and how the patient can book an appointment."
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
        if "slots" in tool_results:
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
            doc_list = tool_results["doctors"].get("doctors", [])
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
