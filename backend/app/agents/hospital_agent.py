import json
from typing import Dict, Any, List, Optional
from google.adk import Agent
from backend.app.tools.hospital_tools import (
    search_hospital_knowledge, get_department, get_hospital_service, get_accepted_insurances
)
from backend.app.config import settings, get_gemini_client


# Google ADK Tools for Hospital Agent
def search_hospital_knowledge_tool(query: str) -> Dict[str, Any]:
    """
    Search the hospital knowledge base (visiting hours, policies, cafeteria, parking, guidelines) using hybrid RAG.
    
    Args:
        query: Questions about hospital hours, amenities, visitor guidelines, or policies.
    """
    return search_hospital_knowledge(query=query)


def get_department_tool(department_name: str = "") -> List[Dict[str, Any]]:
    """
    Look up hospital departments, building locations, floors, and extension phone numbers.
    
    Args:
        department_name: Optional department name filter (e.g. 'Cardiology', 'Emergency', 'Pediatrics').
    """
    return get_department(department_name=department_name if department_name else None)


def get_hospital_service_tool(service_name: str = "") -> List[Dict[str, Any]]:
    """
    Look up hospital diagnostic services, laboratory tests, scans (MRI, CT, X-Ray), and pricing.
    
    Args:
        service_name: Optional service name filter (e.g. 'MRI', 'Blood', 'X-Ray').
    """
    return get_hospital_service(service_name=service_name if service_name else None)


def get_accepted_insurances_tool() -> List[Dict[str, Any]]:
    """
    Retrieves the list of in-network and accepted insurance providers and copay policies.
    """
    return get_accepted_insurances()


# Google ADK Hospital Agent
hospital_agent = Agent(
    name="hospital_agent",
    model=settings.GEMINI_MODEL,
    description="Answers questions about hospital visiting hours, facilities, departments, amenities, insurance networks, and guidelines.",
    instruction=(
        "You are the Hospital Information & Operations Agent for HopeCare General Hospital. "
        "Answer patient questions about visiting hours, cafeteria, parking, directions, departments, services, "
        "and accepted health insurance networks using search_hospital_knowledge_tool, get_department_tool, "
        "get_hospital_service_tool, and get_accepted_insurances_tool. Ground your responses accurately in hospital data."
    ),
    tools=[
        search_hospital_knowledge_tool,
        get_department_tool,
        get_hospital_service_tool,
        get_accepted_insurances_tool
    ]
)


class HospitalAgent:
    name = "Hospital Agent"
    description = "Answers questions about hospital visiting hours, facilities, departments, amenities, insurance networks, and guidelines."
    adk_agent = hospital_agent

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

        # Synthesize grounded answer with Gemini LLM if available
        client = get_gemini_client()
        if client:
            try:
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
