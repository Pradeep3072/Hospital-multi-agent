import json
from typing import Dict, Any
from backend.app.tools.patient_tools import (
    get_current_patient, get_patient_appointments, get_patient_records, get_patient_prescriptions
)
from backend.app.config import settings


class PatientAgent:
    name = "Patient Agent"
    description = "Retrieves authenticated patient profile, active appointments, diagnoses, and medical prescriptions."

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = context.get("patient_id", 1)
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        if "appointment" in msg_lower or "visit" in msg_lower or "booking" in msg_lower:
            tools_called.append("get_patient_appointments")
            tool_results["appointments"] = get_patient_appointments(patient_id)
        elif "prescription" in msg_lower or "medicine" in msg_lower or "drug" in msg_lower or "medication" in msg_lower:
            tools_called.append("get_patient_prescriptions")
            tool_results["prescriptions"] = get_patient_prescriptions(patient_id)
        elif "record" in msg_lower or "diagnosis" in msg_lower or "history" in msg_lower:
            tools_called.append("get_patient_records")
            tool_results["records"] = get_patient_records(patient_id)
        else:
            # General profile query
            tools_called.append("get_current_patient")
            tool_results["profile"] = get_current_patient(patient_id)
            tools_called.append("get_patient_appointments")
            tool_results["appointments"] = get_patient_appointments(patient_id)

        # Gemini LLM synthesis if available
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                prompt = (
                    f"You are the Patient Service Agent for HopeCare General Hospital.\n"
                    f"You are speaking to the authenticated patient (Patient ID: {patient_id}).\n"
                    f"Patient Data:\n{json.dumps(tool_results, indent=2)}\n\n"
                    f"User Message: {message}\n"
                    f"Synthesize a clear, empathetic, and organized summary of their requested health information."
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
            except Exception as e:
                pass

        # Deterministic formatting fallback
        output = []
        if "profile" in tool_results and tool_results["profile"].get("status") == "success":
            p = tool_results["profile"]["patient"]
            output.append(
                f"### Patient Profile: {p['full_name']}\n"
                f"- **Date of Birth**: {p['date_of_birth']} (Gender: {p['gender']})\n"
                f"- **Blood Group**: {p['blood_group']}\n"
                f"- **Emergency Contact**: {p['emergency_contact_name']} ({p['emergency_contact_phone']})\n"
                f"- **Insurance Policy**: {p['insurance_policy_number']}"
            )

        if "appointments" in tool_results:
            appts = tool_results["appointments"].get("appointments", [])
            if appts:
                output.append(f"\n\n### Your Appointments ({len(appts)} total):")
                for a in appts:
                    output.append(
                        f"- **ID #{a['id']}**: {a['doctor_name']} ({a['specialization']}) on **{a['appointment_date']}** at **{a['appointment_time']}** — Status: `{a['status']}`\n"
                        f"  *Reason*: {a['reason_for_visit']}"
                    )
            else:
                output.append("\nYou currently have no scheduled appointments on record.")

        if "prescriptions" in tool_results:
            rxs = tool_results["prescriptions"].get("prescriptions", [])
            if rxs:
                output.append(f"\n\n### Your Active Prescriptions ({len(rxs)} total):")
                for rx in rxs:
                    output.append(
                        f"- **{rx['medication_name']}** ({rx['dosage']}): {rx['frequency']}\n"
                        f"  *Prescribed by*: {rx['prescribed_by']} (Valid: {rx['start_date']} to {rx['end_date']})"
                    )
            else:
                output.append("\nNo active prescriptions found on record.")

        if "records" in tool_results:
            records = tool_results["records"].get("records", [])
            if records:
                output.append(f"\n\n### Medical Records & Diagnoses:")
                for r in records:
                    output.append(
                        f"- **Date {r['record_date']}** by {r['doctor_name']}:\n"
                        f"  *Diagnosis*: {r['diagnosis']}\n"
                        f"  *Summary*: {r['treatment_summary']}"
                    )
            else:
                output.append("\nNo past clinical diagnoses recorded.")

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": "\n".join(output)
        }
