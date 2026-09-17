from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.agents.root_agent import root_supervisor
from backend.app.memory.session_manager import memory_manager

router = APIRouter(prefix="/chat", tags=["Multi-Agent Chat"])


@router.get("/status")
def get_memory_status():
    """
    Returns the operational status of the conversational session memory store (Redis vs In-Memory).
    """
    return memory_manager.get_status()


@router.get("/history/{session_id}")
def get_session_history(session_id: str, limit: int = Query(50, ge=1, le=200)):
    """
    Retrieves recent conversation turns for a session from the short-term cache / database.
    """
    history = memory_manager.get_history(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(history),
        "history": history
    }


@router.get("/sessions")
def list_chat_sessions(patient_id: int = None, limit: int = Query(30, ge=1, le=100)):
    """
    Retrieves all past conversation sessions with summaries, timestamps, and message counts
    for rendering the ChatGPT-style conversation history sidebar.
    """
    sessions = memory_manager.get_all_sessions(patient_id=patient_id, limit=limit)
    return {
        "count": len(sessions),
        "sessions": sessions
    }


@router.delete("/sessions/{session_id}")
@router.delete("/history/{session_id}")
def clear_session_history(session_id: str):
    """
    Flushes the active short-term session memory and database records for a given session.
    """
    cleared = memory_manager.clear_session(session_id)
    return {
        "session_id": session_id,
        "cleared": cleared,
        "message": f"Session memory for '{session_id}' cleared successfully."
    }


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

