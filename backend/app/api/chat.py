from fastapi import APIRouter, HTTPException
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.agents.root_agent import root_supervisor

router = APIRouter(prefix="/chat", tags=["Multi-Agent Chat"])


@router.post("", response_model=ChatResponse)
def handle_chat_message(req: ChatRequest):
    try:
        context = {
            "patient_id": req.patient_id,
            "session_id": req.session_id
        }
        result = root_supervisor.execute_workflow(req.message, context)
        return ChatResponse(
            route=result["route"],
            supervisor=result["supervisor"],
            delegated_agent=result["delegated_agent"],
            is_emergency=result["is_emergency"],
            tools_called=result["tools_called"],
            tool_results=result["tool_results"],
            response=result["response"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")
