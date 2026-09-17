from fastapi import APIRouter, HTTPException
from backend.app.profiles.loader import profile_registry

router = APIRouter(prefix="/profiles", tags=["NeMo Agent Profiles"])


@router.get("")
def list_agent_profiles():
    """
    List all active declarative NeMo agent profiles and behavioral contracts.
    """
    profiles = profile_registry.list_profiles()
    return {
        "count": len(profiles),
        "profiles": [p.model_dump() for p in profiles]
    }


@router.get("/ethos")
def get_clinical_ethos():
    """
    Get the global clinical ethos and safety contract document.
    """
    return {
        "ethos_document": "ETHOS.md",
        "content": profile_registry.get_ethos()
    }


@router.get("/{agent_name}")
def get_agent_profile(agent_name: str):
    """
    Retrieve the detailed specification and YAML contract for a specific agent.
    """
    profile = profile_registry.get_profile(agent_name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent profile '{agent_name}' not found.")
    return profile.model_dump()
