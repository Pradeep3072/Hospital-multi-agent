from typing import List, Dict, Any


def format_chat_history(turns: List[Dict[str, Any]], max_turns: int = 6) -> str:
    """
    Formats a list of conversation turns into a clean markdown dialogue string
    suitable for injecting into agent prompt templates.
    """
    if not turns:
        return "No prior conversation history in this session."

    recent_turns = turns[-max_turns:]
    lines = []
    for turn in recent_turns:
        role = turn.get("role", "user")
        content = turn.get("content", "").strip()
        agent = turn.get("agent_name")
        if role == "user":
            lines.append(f"Patient: {content}")
        else:
            prefix = f"{agent or 'AI Assistant'}"
            lines.append(f"{prefix}: {content}")

    return "\n".join(lines)
