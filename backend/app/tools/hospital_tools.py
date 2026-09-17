from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.rag.retriever import rag_retriever
from backend.app.database.session import SessionLocal
from backend.app.database.models import Department, HospitalService, InsuranceProvider
from backend.app.profiling.profiler import agent_profiler


@agent_profiler.track_tool("search_hospital_knowledge")
def search_hospital_knowledge(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Search hospital knowledge base (visiting hours, rules, policies, guides) using hybrid RAG.
    """
    results = rag_retriever.retrieve(query, top_k=top_k)
    snippets = []
    sources = []
    for r in results:
        snippets.append(f"[{r['header']}]\n{r['content']}")
        if r['source'] not in sources:
            sources.append(r['source'])
    
    return {
        "query": query,
        "results_count": len(results),
        "sources": sources,
        "knowledge": "\n\n---\n\n".join(snippets) if snippets else "No relevant hospital documentation found."
    }


@agent_profiler.track_tool("get_department")
def get_department(department_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get information about hospital departments, locations, and contact info.
    """
    db: Session = SessionLocal()
    try:
        q = db.query(Department)
        if department_name:
            q = q.filter(Department.name.ilike(f"%{department_name}%"))
        depts = q.all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "building": d.location_building,
                "floor": d.floor,
                "phone": d.contact_phone
            }
            for d in depts
        ]
    finally:
        db.close()


@agent_profiler.track_tool("get_hospital_service")
def get_hospital_service(service_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Look up hospital medical services, pricing, and availability hours.
    """
    db: Session = SessionLocal()
    try:
        q = db.query(HospitalService)
        if service_name:
            q = q.filter(HospitalService.name.ilike(f"%{service_name}%"))
        services = q.all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "cost": s.cost,
                "availability": s.availability_hours,
                "department": s.department.name if s.department else "Hospital General"
            }
            for s in services
        ]
    finally:
        db.close()


@agent_profiler.track_tool("get_accepted_insurances")
def get_accepted_insurances() -> List[Dict[str, Any]]:
    """
    List all insurance providers accepted by the hospital.
    """
    db: Session = SessionLocal()
    try:
        providers = db.query(InsuranceProvider).all()
        return [
            {
                "name": p.name,
                "coverage_type": p.coverage_type,
                "network_tier": p.network_tier,
                "contact_phone": p.contact_phone
            }
            for p in providers
        ]
    finally:
        db.close()
