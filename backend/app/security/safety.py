import re
from typing import Tuple, Dict, Any

EMERGENCY_PATTERNS = [
    r"\b(chest\s*pain|heart\s*attack|cardiac\s*arrest)\b",
    r"\b(can'?t\s*breathe|cannot\s*breathe|shortness\s*of\s*breath|severe\s*asthma|choking)\b",
    r"\b(stroke|facial\s*droop|slurred\s*speech|paralysis|sudden\s*numbness)\b",
    r"\b(unconscious|passed\s*out|fainted|unresponsive|seizure|convulsion)\b",
    r"\b(heavy\s*bleeding|profuse\s*bleeding|severe\s*hemorrhage)\b",
    r"\b(suicid|kill\s*myself|end\s*my\s*life|overdose)\b",
    r"\b(severe\s*burn|head\s*trauma|compound\s*fracture)\b"
]


def detect_emergency(user_message: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Rapid deterministic triage check for life-threatening symptoms.
    Bypasses standard conversational and scheduling flows.
    """
    clean_msg = user_message.lower()
    for pattern in EMERGENCY_PATTERNS:
        match = re.search(pattern, clean_msg)
        if match:
            trigger_term = match.group(0)
            return True, {
                "triggered": True,
                "term": trigger_term,
                "protocol": "LEVEL_1_TRAUMA_ESCALATION",
                "instructions": (
                    "EMERGENCY PROTOCOL ACTIVATED:\n\n"
                    "⚠️ If you or the patient are experiencing life-threatening symptoms such as "
                    f"'{trigger_term}', please act immediately:\n\n"
                    "1. Call Emergency Services (911 in the US, 112 in Europe) or your local emergency number immediately.\n"
                    "2. Proceed to the nearest Hospital Emergency Room: HopeCare Emergency & Trauma Center, "
                    "Emergency Wing Ground Floor (24/7). Direct line: (555) 0911.\n"
                    "3. Do NOT attempt to drive yourself. Have an ambulance or companion transport you.\n"
                    "4. If experiencing chest pain, remain seated and calm until emergency responders arrive."
                )
            }
            
    return False, {"triggered": False}
