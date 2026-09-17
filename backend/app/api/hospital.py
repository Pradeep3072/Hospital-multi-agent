from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.tools.hospital_tools import get_department, get_hospital_service, get_accepted_insurances, search_hospital_knowledge

router = APIRouter(prefix="/hospital", tags=["Hospital Info"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@router.get("/departments")
def list_departments():
    return get_department()


@router.get("/services")
def list_services():
    return get_hospital_service()


@router.get("/insurances")
def list_insurances():
    return get_accepted_insurances()


@router.post("/search")
def search_knowledge(req: SearchRequest):
    return search_hospital_knowledge(req.query, top_k=req.top_k)


@router.post("/reindex")
def reindex_knowledge_base():
    """
    Trigger dynamic reload and re-indexing of all documents in data/documents (PDFs, Markdown, text).
    """
    from backend.app.rag.retriever import rag_retriever
    return rag_retriever.reindex()
