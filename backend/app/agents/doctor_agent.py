import json
import re
import datetime
from typing import Dict, Any
from backend.app.tools.doctor_tools import search_doctors, get_doctor_details, get_available_slots
from backend.app.config import settings


class DoctorAgent:
    name = "Doctor Agent"
    description = "Discovers doctors by medical specialty, reviews doctor backgrounds, and retrieves consultation availability."

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        # 1. Check if user is asking for available slots
        date_match = re.search(r"\b(202\d-\d{2}-\d{2})\b", message)
        doc_id_match = re.search(r"\bdoctor\s*(\d+)\b|\bdr\.?\s*(\d+)\b", msg_lower)
        
        # Check for doctor name mentions
        doctor_id = None
        if doc_id_match:
            doctor_id = int(doc_id_match.group(1) or doc_id_match.group(2))

        # Check for specialty keywords
        specialty = None
        for spec in ["cardiologist", "cardiology", "neurologist", "neurology", "pediatrician", "pediatrics", "orthopedic", "orthopedics", "internal medicine", "general"]:
            if spec in msg_lower:
                specialty = spec
                break

        # If date is mentioned or slot query
        if ("slot" in msg_lower or "availability" in msg_lower or "available" in msg_lower or "free" in msg_lower) and (date_match or "tomorrow" in msg_lower or "today" in msg_lower):
            target_date_str = None
            if date_match:
                target_date_str = date_match.group(1)
            elif "tomorrow" in msg_lower:
                tomorrow = datetime.date.today() + datetime.timedelta(days=1)
                target_date_str = str(tomorrow)
            else:
                target_date_str = str(datetime.date.today())

            target_doc_id = doctor_id or 1 # Default to 1 if not specified
            tools_called.append("get_available_slots")
            tool_results["slots"] = get_available_slots(target_doc_id, target_date_str)
            tools_called.append("get_doctor_details")
            tool_results["doctor"] = get_doctor_details(target_doc_id)

        else:
            # Doctor discovery / search
            tools_called.append("search_doctors")
            tool_results["search"] = search_doctors(query=message if not specialty else None, specialty=specialty)

        # Gemini LLM synthesis if key present
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                history_text = context.get("history_text", "")
                history_section = f"Recent Conversation History:\n{history_text}\n\n" if history_text else ""
                prompt = (
                    f"You are the Doctor Discovery Specialist for HopeCare General Hospital.\n"
                    f"{history_section}"
                    f"Doctor Data Retrieved:\n{json.dumps(tool_results, indent=2)}\n\n"
                    f"User Query: {message}\n"
                    f"Present the matching doctors, specialties, consultation fees, and available time slots clearly."
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
            slots_info = tool_results["slots"]
            doc_name = tool_results.get("doctor", {}).get("doctor", {}).get("name", f"Doctor #{slots_info.get('doctor_id')}")
            slots = slots_info.get("slots", [])
            output.append(f"### Available Consultation Slots for {doc_name}\n**Date**: {slots_info.get('date')} ({slots_info.get('day_of_week')})\n")
            if slots:
                output.append(f"We have **{len(slots)} open slots** available:\n`" + "`, `".join(slots) + "`\n\nTo book a slot, tell me: *\"Book appointment with Doctor {doc_name} on {slots_info.get('date')} at [TIME]\"*.")
            else:
                output.append("No open consultation slots remaining on this date. Please try another weekday.")

        elif "search" in tool_results:
            docs = tool_results["search"].get("doctors", [])
            if docs:
                output.append(f"### Found {len(docs)} Matching Doctor(s) at HopeCare:")
                for d in docs:
                    output.append(
                        f"- **{d['name']}** (Doctor ID: `{d['id']}`)\n"
                        f"  *Department*: {d['department']} | *Specialty*: {d['specialization']}\n"
                        f"  *Experience*: {d['experience_years']} yrs | *Fee*: ${d['consultation_fee']:.2f}\n"
                        f"  *Bio*: {d['bio']}\n"
                    )
                output.append("To view available slots, ask: *\"Show available slots for Doctor [ID] on [YYYY-MM-DD]\"*.")
            else:
                output.append("No doctors found matching your criteria. Our departments include Cardiology, Neurology, Pediatrics, Orthopedics, and General Medicine.")

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": "\n".join(output)
        }
