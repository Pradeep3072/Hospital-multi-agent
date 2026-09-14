from typing import Dict, Any
from backend.app.security.safety import detect_emergency


class EmergencyAgent:
    name = "Emergency Agent"
    description = "Detects urgent, high-risk, and life-threatening medical symptoms and executes emergency escalation."

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
