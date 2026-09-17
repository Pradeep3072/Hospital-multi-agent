import pytest
from backend.app.rag.retriever import HybridRAGRetriever
from backend.app.rag.chunking import chunk_document


def test_pdf_chunking_and_indexing():
    retriever = HybridRAGRetriever(doc_dir="data/documents")
    assert retriever.is_indexed
    assert len(retriever.chunks) > 0

    sources = set(c["source"] for c in retriever.chunks)
    assert "Hopecare_Hospital_Information_Document.pdf" in sources


def test_rag_retrieves_pricing_from_pdf():
    retriever = HybridRAGRetriever(doc_dir="data/documents")
    results = retriever.retrieve("What is the price of basic MRI or CT scan?", top_k=3)
    
    assert len(results) > 0
    top_sources = [r["source"] for r in results]
    assert "Hopecare_Hospital_Information_Document.pdf" in top_sources

    content_combined = " ".join([r["content"] for r in results])
    assert "MRI" in content_combined or "CT" in content_combined or "Pricing" in content_combined


def test_rag_retrieves_visiting_hours_from_pdf():
    retriever = HybridRAGRetriever(doc_dir="data/documents")
    results = retriever.retrieve("What are the visiting hours for general wards?", top_k=3)
    
    assert len(results) > 0
    top_headers = [r["header"] for r in results]
    assert any("Visiting Hours" in h or "General Wards" in h for h in top_headers)


def test_rag_reindex_method():
    retriever = HybridRAGRetriever(doc_dir="data/documents")
    stats = retriever.reindex()
    assert stats["status"] == "success"
    assert stats["total_chunks"] > 0
    assert stats["total_documents"] >= 5
    assert "Hopecare_Hospital_Information_Document.pdf" in stats["sources"]
