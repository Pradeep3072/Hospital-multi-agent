import os
import glob
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi

import re
import logging
from backend.app.rag.chunking import chunk_document, chunk_markdown_document
from backend.app.rag.embeddings import EmbeddingModel

logger = logging.getLogger(__name__)

STOP_WORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'of',
    'for', 'to', 'and', 'or', 'what', 'how', 'where', 'which', 'who', 'does',
    'do', 'did', 'as', 'by', 'with', 'from', 'about', 'can', 'could', 'should'
}


class HybridRAGRetriever:
    def __init__(self, doc_dir: str = "data/documents"):
        self.doc_dir = doc_dir
        self.embedding_model = EmbeddingModel()
        self.chunks: List[Dict[str, Any]] = []
        self.corpus_embeddings: np.ndarray = np.array([])
        self.bm25: BM25Okapi = None
        self.is_indexed = False
        self.build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Strip punctuation and stop words for high-accuracy BM25 matching."""
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        filtered = [t for t in tokens if t not in STOP_WORDS]
        return filtered if filtered else tokens

    def build_index(self):
        """Load and index all Markdown, PDF, and text knowledge docs."""
        all_chunks = []
        if not os.path.exists(self.doc_dir):
            os.makedirs(self.doc_dir, exist_ok=True)

        supported_patterns = ["*.md", "*.txt", "*.pdf"]
        doc_files = []
        for pat in supported_patterns:
            doc_files.extend(glob.glob(os.path.join(self.doc_dir, pat)))

        for filepath in doc_files:
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1].lower()

            content = ""
            if ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(filepath)
                    pages_text = []
                    for page in reader.pages:
                        t = page.extract_text() or ""
                        if t.strip():
                            pages_text.append(t.strip())
                    content = "\n\n".join(pages_text)
                except Exception as e:
                    logger.error(f"Failed to read PDF document {filename}: {e}")
                    content = ""
            else:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read text document {filename}: {e}")
                    content = ""

            if content.strip():
                chunks = chunk_document(content, filename)
                all_chunks.extend(chunks)

        if not all_chunks:
            # Fallback if docs are empty
            all_chunks.append({
                "chunk_id": "default_1",
                "source": "general.md",
                "header": "HopeCare General Info",
                "content": "HopeCare General Hospital provides comprehensive tertiary healthcare 24/7."
            })

        self.chunks = all_chunks

        # 1. BM25 Tokenization with punctuation & stop word filtering
        tokenized_corpus = [self._tokenize(c["content"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 2. Dense Embeddings
        texts = [c["content"] for c in self.chunks]
        self.corpus_embeddings = self.embedding_model.embed_documents(texts)
        self.is_indexed = True

    def reindex(self) -> Dict[str, Any]:
        """Re-scan documents directory and rebuild search indices."""
        self.build_index()
        sources = sorted(list(set(c["source"] for c in self.chunks)))
        return {
            "status": "success",
            "total_chunks": len(self.chunks),
            "total_documents": len(sources),
            "sources": sources
        }

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Hybrid Retrieval combining normalized BM25 keyword scoring and dense vector projection.
        """
        if not self.is_indexed or len(self.chunks) == 0:
            return []

        # A. BM25 scoring & ranking
        query_tokens = self._tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(query_tokens))
        bm_max = np.max(bm25_scores) if len(bm25_scores) > 0 and np.max(bm25_scores) > 0 else 1.0
        bm_norm = bm25_scores / bm_max

        # B. Dense vector cosine scoring & ranking
        query_vec = self.embedding_model.embed_query(query)
        dense_scores = np.dot(self.corpus_embeddings, query_vec)
        dense_min = np.min(dense_scores) if len(dense_scores) > 0 else 0.0
        dense_max = np.max(dense_scores) if len(dense_scores) > 0 else 1.0
        dense_range = dense_max - dense_min
        dense_norm = (dense_scores - dense_min) / dense_range if dense_range > 0 else np.zeros_like(dense_scores)

        # C. Combined Hybrid Scoring (65% BM25 lexical precision + 35% semantic projection)
        hybrid_scores = 0.65 * bm_norm + 0.35 * dense_norm
        ranked_indices = np.argsort(hybrid_scores)[::-1]

        results = []
        for idx in ranked_indices[:top_k]:
            chunk_data = self.chunks[idx].copy()
            chunk_data["score"] = float(hybrid_scores[idx])
            chunk_data["dense_score"] = float(dense_scores[idx])
            chunk_data["bm25_score"] = float(bm25_scores[idx])
            results.append(chunk_data)

        return results


# Global singleton instance
rag_retriever = HybridRAGRetriever()
