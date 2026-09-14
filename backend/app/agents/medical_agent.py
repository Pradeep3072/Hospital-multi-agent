import json
from typing import Dict, Any
from backend.app.rag.retriever import rag_retriever
from backend.app.config import settings


class MedicalKnowledgeAgent:
    name = "Medical Knowledge Agent"
    description = "Provides hospital-approved general patient health education, lifestyle guidance, and post-operative tips."

    def process(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        tools_called = ["search_approved_medical_kb"]
        results = rag_retriever.retrieve(f"medical health {message}", top_k=3)
        tool_results = {"retrieved_guidelines": results}

        # Format retrieved knowledge
        knowledge_texts = [f"[{r['header']}]\n{r['content']}" for r in results]
        knowledge_summary = "\n\n".join(knowledge_texts)

        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
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

        # Deterministic grounded fallback
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
