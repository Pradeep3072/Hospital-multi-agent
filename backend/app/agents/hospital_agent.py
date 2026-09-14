import json
from typing import Dict, Any
from backend.app.tools.hospital_tools import (
    search_hospital_knowledge, get_department, get_hospital_service, get_accepted_insurances
)
from backend.app.config import settings


class HospitalAgent:
    name = "Hospital Agent"
    description = "Answers questions about hospital visiting hours, facilities, departments, amenities, insurance networks, and guidelines."

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        msg_lower = message.lower()
        tools_called = []
        tool_results = {}

        # Determine appropriate tool
        if "insurance" in msg_lower or "coverage" in msg_lower or "pay" in msg_lower:
            tools_called.append("get_accepted_insurances")
            tool_results["insurances"] = get_accepted_insurances()
            tools_called.append("search_hospital_knowledge")
            tool_results["rag"] = search_hospital_knowledge(message)
        elif "department" in msg_lower or "wing" in msg_lower or "floor" in msg_lower or "building" in msg_lower:
            tools_called.append("get_department")
            tool_results["departments"] = get_department()
            tools_called.append("search_hospital_knowledge")
            tool_results["rag"] = search_hospital_knowledge(message)
        elif "service" in msg_lower or "mri" in msg_lower or "x-ray" in msg_lower or "test" in msg_lower or "cost" in msg_lower:
            tools_called.append("get_hospital_service")
            tool_results["services"] = get_hospital_service()
        else:
            tools_called.append("search_hospital_knowledge")
            tool_results["rag"] = search_hospital_knowledge(message)

        # Synthesize grounded answer
        # If Gemini API key is configured, invoke Gemini with grounded tool context
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                history_text = context.get("history_text", "")
                history_section = f"Recent Conversation History:\n{history_text}\n\n" if history_text else ""
                prompt = (
                    f"You are the Hospital Information Agent for HopeCare General Hospital.\n"
                    f"Answer the user's question accurately using the provided hospital knowledge and conversation context:\n"
                    f"{history_section}"
                    f"Tool Findings:\n{json.dumps(tool_results, indent=2)}\n\n"
                    f"User Query: {message}\n"
                    f"Provide a warm, professional, and well-formatted response with bullet points if helpful."
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
                print(f"Notice: Gemini call failed ({e}), using grounded synthesizer fallback.")

        # Grounded deterministic synthesis fallback
        synthesized_parts = []
        if "rag" in tool_results and tool_results["rag"].get("knowledge"):
            knowledge = tool_results["rag"]["knowledge"]
            synthesized_parts.append(f"Here is the hospital information regarding your inquiry:\n\n{knowledge}")

        if "insurances" in tool_results:
            prov_names = [p["name"] for p in tool_results["insurances"]]
            synthesized_parts.append(f"\n\n**Accepted Insurance Providers**:\n- " + "\n- ".join(prov_names))

        if "services" in tool_results:
            services_list = [f"- **{s['name']}** ({s['department']}): ${s['cost']:.2f} — {s['description']}" for s in tool_results["services"]]
            synthesized_parts.append("\n\n**Available Hospital Services & Pricing**:\n" + "\n".join(services_list))

        if not synthesized_parts:
            synthesized_parts.append("HopeCare General Hospital is open 24/7 for emergency care. General visiting hours are 10:00 AM to 8:00 PM daily.")

        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": "\n\n".join(synthesized_parts)
        }
