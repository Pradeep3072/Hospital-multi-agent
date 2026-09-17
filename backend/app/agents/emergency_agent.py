from typing import Dict, Any
from google.adk import Agent
from backend.app.security.safety import detect_emergency
from backend.app.config import settings


def emergency_triage_tool(symptoms: str) -> Dict[str, Any]:
    """
    Evaluates acute or severe medical symptoms for life-threatening emergencies.
    
    Args:
        symptoms: Description of the patient's symptoms (e.g. chest pain, shortness of breath).
    """
    is_emergency, triage_data = detect_emergency(symptoms)
    return {
        "is_emergency": is_emergency,
        "triage_data": triage_data,
        "instructions": triage_data.get(
            "instructions",
            "⚠️ **EMERGENCY PROTOCOL ACTIVATED**: Please call 911 or proceed to the nearest Emergency Wing immediately."
        )
    }


# Google ADK Agent Definition
emergency_agent = Agent(
    name="emergency_agent",
    model=settings.GEMINI_MODEL,
    description="Detects urgent, high-risk, and life-threatening medical symptoms and executes emergency escalation protocols.",
    instruction=(
        "You are the Emergency Triage Agent for HopeCare General Hospital. "
        "Your top priority is patient safety. Use the emergency_triage_tool to evaluate critical symptoms like chest pain, "
        "shortness of breath, loss of consciousness, stroke signs, or severe trauma. "
        "Always provide urgent escalation guidance when an emergency is detected."
    ),
    tools=[emergency_triage_tool]
)


class EmergencyAgent:
    name = "Emergency Agent"
    description = "Detects urgent, high-risk, and life-threatening medical symptoms and executes emergency escalation."
    adk_agent = emergency_agent

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        is_emergency, triage_data = detect_emergency(message)
        
        if is_emergency:
            return {
                "agent": self.name,
                "is_emergency": True,
                "tool_called": "emergency_triage_escalation",
                "tool_result": triage_data,
                "response": triage_data["instructions"]
            }
        
        return {
            "agent": self.name,
            "is_emergency": False,
            "tool_called": None,
            "tool_result": None,
            "response": (
                "If you feel this is a medical emergency, please call 911 or visit our Emergency Wing immediately. "
                "Otherwise, I can connect you to our Doctor or Appointment agents."
            )
        }
