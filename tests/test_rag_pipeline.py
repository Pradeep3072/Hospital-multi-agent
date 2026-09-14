from backend.app.rag.retriever import rag_retriever


def test_rag_retriever_visiting_hours():
    results = rag_retriever.retrieve("What are the ICU visiting hours?")
    assert len(results) > 0
    combined = " ".join([r["content"] for r in results])
    headers = [r["header"] for r in results]
    assert "12:00 PM" in combined or any("Visiting Hours" in h for h in headers)


def test_rag_retriever_insurance():
    results = rag_retriever.retrieve("Do you take Blue Cross Blue Shield?")
    assert len(results) > 0
    content = " ".join([r["content"] for r in results])
    assert "Blue Cross" in content or "Insurance" in content
