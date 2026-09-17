import json
from typing import Dict, Any
from google.adk import Agent
from backend.app.tools.patient_tools import (
    get_current_patient, get_patient_appointments, get_patient_records, get_patient_prescriptions
)
from backend.app.config import settings, get_gemini_client


# Google ADK Tools for Patient Agent
def get_current_patient_tool(patient_id: int = 1) -> Dict[str, Any]:
    """
    Retrieves the authenticated patient's profile overview, blood group, emergency contact, and insurance details.
    
    Args:
        patient_id: The numeric ID of the patient (defaults to 1 for active patient).
    """
    return get_current_patient(patient_id=patient_id)


def get_patient_appointments_tool(patient_id: int = 1) -> Dict[str, Any]:
    """
    Retrieves all scheduled, completed, and upcoming appointments for the patient.
    
    Args:
        patient_id: The numeric ID of the patient.
    """
    return get_patient_appointments(patient_id=patient_id)


def get_patient_records_tool(patient_id: int = 1) -> Dict[str, Any]:
    """
    Retrieves past clinical diagnoses, vital history, and physician visit summaries for the patient.
    
    Args:
        patient_id: The numeric ID of the patient.
    """
    return get_patient_records(patient_id=patient_id)


def get_patient_prescriptions_tool(patient_id: int = 1) -> Dict[str, Any]:
    """
    Retrieves active medical prescriptions, dosage, frequency, and instructions for the patient.
    
    Args:
        patient_id: The numeric ID of the patient.
    """
    return get_patient_prescriptions(patient_id=patient_id)


# Google ADK Patient Agent
patient_agent = Agent(
    name="patient_agent",
    model=settings.GEMINI_MODEL,
    description="Retrieves authenticated patient profile, active appointments, diagnoses, and medical prescriptions.",
    instruction=(
        "You are the Patient Service Agent for HopeCare General Hospital. "
        "You assist authenticated patients in reviewing their health profile, medical history, past visits, "
        "and active prescriptions using get_current_patient_tool, get_patient_appointments_tool, "
        "get_patient_records_tool, and get_patient_prescriptions_tool. "
        "Always summarize medical prescriptions with medication name, dosage, and frequency clearly."
    ),
    tools=[
        get_current_patient_tool,
        get_patient_appointments_tool,
        get_patient_records_tool,
        get_patient_prescriptions_tool
    ]
)


class PatientAgent:
    name = "Patient Agent"
    description = "Retrieves authenticated patient profile, active appointments, diagnoses, and medical prescriptions."
    adk_agent = patient_agent

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
            tools_called.append("get_current_patient")
            tool_results["profile"] = get_current_patient(patient_id)
            tools_called.append("get_patient_appointments")
            tool_results["appointments"] = get_patient_appointments(patient_id)

        client = get_gemini_client()
        if client:
            try:
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
            except Exception:
                pass

        # Deterministic formatting fallback
        output = []
        if "prescriptions" in tool_results:
            rx_list = tool_results["prescriptions"].get("prescriptions", [])
            if rx_list:
                output.append("### Active Prescriptions\n")
                for rx in rx_list:
                    prescribed = f" (Prescribed by: {rx['prescribed_by']})" if rx.get("prescribed_by") else ""
                    output.append(
                        f"- 💊 **{rx.get('medication_name', 'Medication')}** ({rx.get('dosage', 'Standard')}) — *{rx.get('frequency', 'Daily')}*{prescribed}\n"
                        f"  - Duration: {rx.get('start_date')} to {rx.get('end_date', 'Ongoing')}\n"
                    )
            else:
                output.append("You currently have no active prescriptions on file.")

        elif "appointments" in tool_results:
            appts = tool_results["appointments"].get("appointments", [])
            if appts:
                output.append("### Your Appointments\n")
                for a in appts:
                    output.append(
                        f"- 🗓️ **Appointment #{a['appointment_id']}** with **Dr. {a['doctor_name']}** ({a['specialization']})\n"
                        f"  - Date & Time: {a['appointment_date']} at {a['appointment_time']}\n"
                        f"  - Status: `{a['status']}` | Reason: {a['reason_for_visit']}\n"
                    )
            else:
                output.append("You have no scheduled appointments.")

        elif "records" in tool_results:
            recs = tool_results["records"].get("records", [])
            if recs:
                output.append("### Medical Records & Diagnoses\n")
                for r in recs:
                    treatment = r.get('treatment_summary') or r.get('treatment_plan', 'Follow-up')
                    symptoms = f"  - Symptoms: {r['symptoms']}\n" if r.get('symptoms') else ""
                    output.append(
                        f"- 📋 **{r.get('diagnosis', 'Diagnosis')}** (Recorded on {r.get('record_date')})\n"
                        f"{symptoms}"
                        f"  - Treatment: {treatment}\n"
                    )
            else:
                output.append("No prior medical records found.")

        elif "profile" in tool_results:
            p = tool_results["profile"].get("patient", {})
            if p:
                output.append(
                    f"### Patient Profile: {p.get('name')}\n"
                    f"- **Email**: {p.get('email')} | **Phone**: {p.get('phone')}\n"
                    f"- **DOB**: {p.get('date_of_birth')} | **Gender**: {p.get('gender')}\n"
                    f"- **Blood Group**: {p.get('blood_group')}\n"
                    f"- **Insurance**: {p.get('insurance_provider')} (Policy: `{p.get('insurance_policy_number')}`)\n"
                    f"- **Emergency Contact**: {p.get('emergency_contact_name')} ({p.get('emergency_contact_phone')})\n"
                )
            else:
                output.append("Unable to load patient profile.")

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": "\n".join(output)
        }
