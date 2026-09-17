import os
import re
import time
from typing import Dict, Any, Optional, List

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.app.config import settings
from backend.app.security.safety import detect_emergency
from backend.app.profiling.profiler import agent_profiler
from backend.app.agents.emergency_agent import EmergencyAgent, emergency_agent
from backend.app.agents.hospital_agent import HospitalAgent, hospital_agent
from backend.app.agents.patient_agent import PatientAgent, patient_agent
from backend.app.agents.doctor_agent import DoctorAgent, doctor_agent
from backend.app.agents.appointment_agent import AppointmentAgent, appointment_agent
from backend.app.agents.medical_agent import MedicalKnowledgeAgent, medical_agent
from backend.app.memory.session_manager import memory_manager
from backend.app.memory.context_window import format_chat_history


# Mapping between Google ADK internal agent names and display names
AGENT_NAME_MAP = {
    "emergency_agent": "Emergency Agent",
    "appointment_agent": "Appointment Agent",
    "doctor_agent": "Doctor Agent",
    "patient_agent": "Patient Agent",
    "hospital_agent": "Hospital Agent",
    "medical_agent": "Medical Knowledge Agent",
    "root_supervisor": "Root Supervisor Agent"
}

AGENT_ROUTE_MAP = {
    "emergency_agent": "emergency",
    "appointment_agent": "appointment",
    "doctor_agent": "doctor",
    "patient_agent": "patient",
    "hospital_agent": "hospital",
    "medical_agent": "medical"
}

# Google ADK Root Supervisor Definition
adk_root_agent = Agent(
    name="root_supervisor",
    model=settings.GEMINI_MODEL,
    description="Google ADK Root Orchestrator: Detects intent, coordinates specialized sub-agents, manages workflow state.",
    instruction=(
        "You are the Root Supervisor Hospital AI for HopeCare General Hospital. "
        "Coordinate and delegate user queries to the appropriate specialized sub-agent:\n"
        "- emergency_agent: Urgent life-threatening symptoms (chest pain, stroke, severe trauma, shortness of breath).\n"
        "- appointment_agent: Booking, cancelling, rescheduling appointments, or selecting consultation slots.\n"
        "- doctor_agent: Finding doctors by specialty, viewing physician credentials/fees, and checking schedules.\n"
        "- patient_agent: Authenticated patient profiles, active prescriptions, medical history, and past appointments.\n"
        "- hospital_agent: Visiting hours, cafeteria, parking, departments, diagnostic services, and accepted insurances.\n"
        "- medical_agent: Approved general health education, diabetes/hypertension guides, and post-op wound care.\n"
        "Delegate to the specialized sub-agent using transfer_to_agent to formulate the answer."
    ),
    sub_agents=[
        emergency_agent,
        appointment_agent,
        doctor_agent,
        patient_agent,
        hospital_agent,
        medical_agent
    ]
)

# Google ADK Session & Runner Runtime
adk_session_service = InMemorySessionService()
adk_runner = Runner(
    agent=adk_root_agent,
    app_name="hospital_multi_agent_system",
    session_service=adk_session_service,
    auto_create_session=True
)


class RootSupervisorAgent:
    name = "Root Supervisor Agent"
    description = "Google ADK Root Orchestrator: Detects intent, coordinates specialized sub-agents, manages workflow state."
    adk_agent = adk_root_agent
    adk_runner = adk_runner

    def __init__(self):
        self.emergency_agent = EmergencyAgent()
        self.hospital_agent = HospitalAgent()
        self.patient_agent = PatientAgent()
        self.doctor_agent = DoctorAgent()
        self.appointment_agent = AppointmentAgent()
        self.medical_agent = MedicalKnowledgeAgent()

    def route_intent(self, message: str, pre_checked_emergency: bool = False) -> str:
        """
        Deterministic intent classifier used for offline fallback and fast routing.
        """
        msg = message.lower()

        # 1. Emergency symptoms
        if not pre_checked_emergency:
            is_emerg, _ = detect_emergency(message)
            if is_emerg:
                return "emergency"

        # 2. Patient Specific Records, Prescriptions, My Appointments
        if any(w in msg for w in [
            "prescription", "prescriptions", "medication", "my appointment", "my appointments",
            "my profile", "my record", "my records", "my medicine", "my history", 
            "my doctor", "my health", "diagnosis", "diagnoses", "past appointment"
        ]):
            return "patient"

        # 3. Appointment Booking / Rescheduling / Cancellation / Slot Requests
        if any(w in msg for w in [
            "book", "bok", "booking", "schedule", "reschedule", "cancel", "reserve", 
            "appointment", "consultation", "slots", "slot"
        ]):
            return "appointment"

        # 4. Doctor Search / Discovery / Specialty
        if any(w in msg for w in [
            "doctor", "dr.", "cardiologist", "cardiology", "neurologist", "neurology", 
            "pediatrician", "pediatrics", "surgeon", "orthopedic", "orthopedics", 
            "internal medicine", "physician", "find a doctor", "specialist"
        ]):
            return "doctor"

        # 5. General Medical Education
        if any(w in msg for w in [
            "blood pressure tip", "hypertension", "diabetes guide", "wound care", 
            "diet tip", "lifestyle", "how to manage"
        ]):
            return "medical"

        # 6. Hospital Info / Facilities / Visiting / Insurance
        return "hospital"

    def execute_workflow(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes multi-agent workflow using Google ADK Runner with emergency fast-path and fallback,
        fully profiled with NVIDIA NeMo-style execution telemetry and step latency tracking.
        """
        if context is None:
            context = {}

        patient_id = context.get("patient_id", 1)
        session_id = context.get("session_id", "default-session")

        trace = agent_profiler.start_trace(session_id, patient_id, message)

        # Load recent context history
        t_hist_start = time.time()
        recent_turns = memory_manager.get_history(session_id, limit=6)
        context["history"] = recent_turns
        context["history_text"] = format_chat_history(recent_turns, max_turns=6)
        t_hist_end = time.time()
        trace.add_event("memory_session.get_history", "memory_io", t_hist_start, t_hist_end, details={"turns_loaded": len(recent_turns)})

        # 1. Fast-Path Emergency Pre-Check (Zero-latency medical safety)
        t_safety_start = time.time()
        is_emerg, triage_data = detect_emergency(message)
        t_safety_end = time.time()
        trace.add_event("safety_check.detect_emergency", "safety_check", t_safety_start, t_safety_end, details={"is_emergency": is_emerg})

        if is_emerg:
            emerg_resp = triage_data.get(
                "instructions",
                "⚠️ **EMERGENCY PROTOCOL ACTIVATED**: Please call 911 or visit the nearest Emergency Wing immediately."
            )
            t_mem_start = time.time()
            self._save_memory(session_id, patient_id, message, emerg_resp, "Emergency Agent")
            t_mem_end = time.time()
            trace.add_event("memory_session.add_turn", "memory_io", t_mem_start, t_mem_end)

            trace.finalize("emergency", "Emergency Agent", emerg_resp, ["emergency_triage_tool"], is_emergency=True)
            agent_profiler.record_trace(trace)

            return {
                "route": "emergency",
                "supervisor": self.name,
                "delegated_agent": "Emergency Agent",
                "is_emergency": True,
                "tools_called": ["emergency_triage_tool"],
                "tool_results": triage_data,
                "response": emerg_resp
            }

        # 2. Execute via Google ADK Runner if API key is active
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                adk_message = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[Active Patient ID: {patient_id}]\n{message}")]
                )
                
                delegated_adk_name = "root_supervisor"
                tools_called: List[str] = []
                tool_results: Dict[str, Any] = {}
                response_text = ""

                t_adk_start = time.time()
                for event in self.adk_runner.run(
                    user_id=f"patient_{patient_id}",
                    session_id=session_id,
                    new_message=adk_message
                ):
                    if event.actions and event.actions.transfer_to_agent:
                        delegated_adk_name = event.actions.transfer_to_agent
                    elif event.author and event.author != "root_supervisor":
                        delegated_adk_name = event.author

                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.function_call:
                                tools_called.append(part.function_call.name)
                            if part.function_response:
                                call_key = tools_called[-1] if tools_called else "result"
                                tool_results[call_key] = part.function_response.response
                            if part.text:
                                response_text += part.text
                t_adk_end = time.time()

                delegated_display = AGENT_NAME_MAP.get(delegated_adk_name, "Hospital Agent")
                route = AGENT_ROUTE_MAP.get(delegated_adk_name, self.route_intent(message, pre_checked_emergency=True))
                trace.add_event("adk_orchestration.run", "agent_execution", t_adk_start, t_adk_end, details={"agent": delegated_display, "tools": tools_called})

                if response_text.strip():
                    t_mem_start = time.time()
                    self._save_memory(session_id, patient_id, message, response_text, delegated_display)
                    t_mem_end = time.time()
                    trace.add_event("memory_session.add_turn", "memory_io", t_mem_start, t_mem_end)

                    trace.finalize(route, delegated_display, response_text, tools_called, is_emergency=False)
                    agent_profiler.record_trace(trace)

                    return {
                        "route": route,
                        "supervisor": self.name,
                        "delegated_agent": delegated_display,
                        "is_emergency": False,
                        "tools_called": tools_called,
                        "tool_results": tool_results,
                        "response": response_text
                    }
            except Exception as e:
                # Log notice and seamlessly use deterministic agent fallback
                print(f"Notice: Google ADK live execution exception ({e}). Falling back to sub-agent handler.")

        # 3. Deterministic Sub-Agent Fallback
        t_route_start = time.time()
        route = self.route_intent(message, pre_checked_emergency=True)
        t_route_end = time.time()
        trace.add_event("supervisor.route_intent", "routing", t_route_start, t_route_end, details={"route": route})

        t_agent_start = time.time()
        if route == "appointment":
            res = self.appointment_agent.process(message, context)
        elif route == "patient":
            res = self.patient_agent.process(message, context)
        elif route == "doctor":
            res = self.doctor_agent.process(message, context)
        elif route == "medical":
            res = self.medical_agent.process(message, context)
        else:
            res = self.hospital_agent.process(message, context)
        t_agent_end = time.time()

        agent_name = res.get("agent", "Hospital Agent")
        tools_called = res.get("tools_called", [])
        trace.add_event(f"{agent_name}.process", "agent_execution", t_agent_start, t_agent_end, details={"tools": tools_called})

        t_mem_start = time.time()
        self._save_memory(session_id, patient_id, message, res["response"], agent_name)
        t_mem_end = time.time()
        trace.add_event("memory_session.add_turn", "memory_io", t_mem_start, t_mem_end)

        trace.finalize(route, agent_name, res["response"], tools_called, is_emergency=False)
        agent_profiler.record_trace(trace)

        return {
            "route": route,
            "supervisor": self.name,
            "delegated_agent": agent_name,
            "is_emergency": False,
            "tools_called": tools_called,
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
