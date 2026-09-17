import json
from typing import Dict, Any
from google.adk import Agent
from backend.app.rag.retriever import rag_retriever
from backend.app.config import settings, get_gemini_client


# Google ADK Tool for Medical Knowledge Agent
def search_approved_medical_kb_tool(query: str) -> Dict[str, Any]:
    """
    Retrieves approved hospital clinical health guidelines, chronic disease care, wound care, and recovery instructions.
    
    Args:
        query: Medical topic or health education query (e.g. 'hypertension diet', 'post-op wound care', 'diabetes management').
    """
    results = rag_retriever.retrieve(f"medical health {query}", top_k=3)
    knowledge_texts = [f"[{r['header']}]\n{r['content']}" for r in results]
    return {
        "query": query,
        "results_count": len(results),
        "guidelines": results,
        "summary": "\n\n".join(knowledge_texts)
    }


# Google ADK Medical Knowledge Agent
medical_agent = Agent(
    name="medical_agent",
    model=settings.GEMINI_MODEL,
    description="Provides hospital-approved general patient health education, lifestyle guidance, and post-operative tips.",
    instruction=(
        "You are the Medical Knowledge & Education Agent for HopeCare General Hospital. "
        "Provide patient education on chronic conditions (hypertension, diabetes), general wellness, and recovery guidelines "
        "using search_approved_medical_kb_tool. "
        "Always include an explicit medical disclaimer stating that this information is educational and does not replace "
        "an in-person physician diagnosis or emergency care."
    ),
    tools=[search_approved_medical_kb_tool]
)


class MedicalKnowledgeAgent:
    name = "Medical Knowledge Agent"
    description = "Provides hospital-approved general patient health education, lifestyle guidance, and post-operative tips."
    adk_agent = medical_agent

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        tools_called = ["search_approved_medical_kb"]
        results = rag_retriever.retrieve(f"medical health {message}", top_k=3)
        tool_results = {"retrieved_guidelines": results}

        knowledge_texts = [f"[{r['header']}]\n{r['content']}" for r in results]
        knowledge_summary = "\n\n".join(knowledge_texts)

        client = get_gemini_client()
        if client:
            try:
                prompt = (
                    f"You are the Medical Knowledge Agent for HopeCare General Hospital.\n"
                    f"Ground your answer strictly in these approved clinical guidelines:\n{knowledge_summary}\n\n"
                    f"User Inquiry: {message}\n"
                    f"Provide a clear, helpful, educational response and always advise that this is for general education and does not replace in-person physician consultation."
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

        disclaimer = (
            "\n\n*Medical Disclaimer: This information is for general patient education from approved HopeCare Hospital guidelines "
            "and does not replace a clinical examination or diagnosis. If you have severe symptoms, contact your doctor immediately.*"
        )
        return {
            "agent": self.name,
            "tools_called": tools_called,
            "tool_results": tool_results,
            "response": f"### Hospital Approved Health Education:\n\n{knowledge_summary}{disclaimer}"
        }
