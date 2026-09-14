import re
from typing import Dict, Any, Optional

from backend.app.agents.emergency_agent import EmergencyAgent
from backend.app.agents.hospital_agent import HospitalAgent
from backend.app.agents.patient_agent import PatientAgent
from backend.app.agents.doctor_agent import DoctorAgent
from backend.app.agents.appointment_agent import AppointmentAgent
from backend.app.agents.medical_agent import MedicalKnowledgeAgent
from backend.app.database.session import SessionLocal
from backend.app.database.models import Conversation, MemoryRecord
from backend.app.memory.session_manager import memory_manager
from backend.app.memory.context_window import format_chat_history


class RootSupervisorAgent:
    name = "Root Supervisor Agent"
    description = "Google ADK Root Orchestrator: Detects intent, coordinates specialized sub-agents, manages workflow state."

    def __init__(self):
        self.emergency_agent = EmergencyAgent()
        self.hospital_agent = HospitalAgent()
        self.patient_agent = PatientAgent()
        self.doctor_agent = DoctorAgent()
        self.appointment_agent = AppointmentAgent()
        self.medical_agent = MedicalKnowledgeAgent()

    def route_intent(self, message: str) -> str:
        """
        Classifies incoming user intent into domain sub-agent routes.
        """
        msg = message.lower()

        # 1. First Priority: Life-threatening Emergency symptoms
        is_emerg, _ = self.emergency_agent.process(message, {})["is_emergency"], None
        if is_emerg:
            return "emergency"

        # 2. Appointment Booking / Rescheduling / Cancellation
        if any(w in msg for w in ["cancel", "reschedule", "book appointment", "reserve", "book with", "schedule appointment"]):
            return "appointment"

        # 3. Patient Specific Records, Prescriptions, My Appointments
        if any(w in msg for w in [
            "prescription", "prescriptions", "medication", "my appointment", 
            "my profile", "my record", "my records", "my medicine", "my history", 
            "my doctor", "my health", "diagnosis", "diagnoses"
        ]):
            return "patient"

        # 4. Doctor Search / Availability / Specialty
        if any(w in msg for w in ["doctor", "dr.", "cardiologist", "neurologist", "pediatrician", "surgeon", "available slots", "find a doctor", "specialist"]):
            # If specifically asking to book with doctor, route to appointment
            if "book" in msg:
                return "appointment"
            return "doctor"

        # 5. General Medical Education
        if any(w in msg for w in ["blood pressure tip", "hypertension", "diabetes guide", "wound care", "diet tip", "lifestyle", "how to manage"]):
            return "medical"

        # 6. Hospital Info / Facilities / Visiting / Insurance
        if any(w in msg for w in ["visiting", "hours", "timing", "cafeteria", "parking", "insurance", "policy", "department", "pharmacy", "service"]):
            return "hospital"

        # Default fallback: Hospital Knowledge / General
        return "hospital"

    def execute_workflow(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main execution workflow orchestrator
        """
        if context is None:
            context = {}

        patient_id = context.get("patient_id", 1)
        session_id = context.get("session_id", "default-session")

        # Load recent sliding context window from short-term memory
        recent_turns = memory_manager.get_history(session_id, limit=6)
        context["history"] = recent_turns
        context["history_text"] = format_chat_history(recent_turns, max_turns=6)

        # 1. Emergency Pre-Check
        emerg_result = self.emergency_agent.process(message, context)
        if emerg_result.get("is_emergency"):
            self._save_memory(session_id, patient_id, message, emerg_result["response"], "Emergency Agent")
            return {
                "route": "emergency",
                "supervisor": self.name,
                "delegated_agent": self.emergency_agent.name,
                "is_emergency": True,
                "tools_called": [emerg_result.get("tool_called")],
                "tool_results": emerg_result.get("tool_result"),
                "response": emerg_result["response"]
            }

        # 2. Intent Routing
        route = self.route_intent(message)

        # 3. Sub-Agent Execution
        if route == "appointment":
            res = self.appointment_agent.process(message, context)
        elif route == "patient":
            res = self.patient_agent.process(message, context)
        elif route == "doctor":
            res = self.doctor_agent.process(message, context)
        elif route == "medical":
            res = self.medical_agent.process(message, context)
        else: # "hospital"
            res = self.hospital_agent.process(message, context)

        # 4. Save to Conversation Memory
        self._save_memory(session_id, patient_id, message, res["response"], res.get("agent", "Root Supervisor"))

        return {
            "route": route,
            "supervisor": self.name,
            "delegated_agent": res.get("agent"),
            "is_emergency": False,
            "tools_called": res.get("tools_called", []),
            "tool_results": res.get("tool_results", {}),
            "response": res["response"]
        }

    def _save_memory(self, session_id: str, patient_id: int, user_msg: str, agent_response: str, agent_name: str):
        """
        Record conversation turns into Redis / in-memory cache and relational database.
        """
        memory_manager.add_turn(
            session_id=session_id,
            role="user",
            content=user_msg,
            agent_name=None,
            patient_id=patient_id
        )
        memory_manager.add_turn(
            session_id=session_id,
            role="agent",
            content=agent_response,
            agent_name=agent_name,
            patient_id=patient_id
        )


# Global supervisor instance
root_supervisor = RootSupervisorAgent()
