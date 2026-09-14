import os
import glob
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi

from backend.app.rag.chunking import chunk_markdown_document
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.config import settings


class HybridRAGRetriever:
    def __init__(self, doc_dir: str = "data/documents"):
        self.doc_dir = doc_dir
        self.embedding_model = EmbeddingModel()
        self.chunks: List[Dict[str, Any]] = []
        self.corpus_embeddings: np.ndarray = np.array([])
        self.bm25: BM25Okapi = None
        self.is_indexed = False
        self.build_index()

    def build_index(self):
        """Load and index all markdown knowledge docs"""
        all_chunks = []
        if not os.path.exists(self.doc_dir):
            os.makedirs(self.doc_dir, exist_ok=True)
            
        doc_files = glob.glob(os.path.join(self.doc_dir, "*.md"))
        for filepath in doc_files:
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = chunk_markdown_document(content, filename)
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
        
        # 1. BM25 Tokenization
        tokenized_corpus = [c["content"].lower().split() for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 2. Dense Embeddings
        texts = [c["content"] for c in self.chunks]
        self.corpus_embeddings = self.embedding_model.embed_documents(texts)
        self.is_indexed = True

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
        """
        if not self.is_indexed or len(self.chunks) == 0:
            return []

        # A. BM25 scoring & ranking
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_ranked = np.argsort(bm25_scores)[::-1]

        # B. Dense vector cosine scoring & ranking
        query_vec = self.embedding_model.embed_query(query)
        # Cosine similarity (both vectors are L2-normalized)
        dense_scores = np.dot(self.corpus_embeddings, query_vec)
        dense_ranked = np.argsort(dense_scores)[::-1]

        # C. Reciprocal Rank Fusion (RRF)
        # score = 1 / (k + rank_bm25) + 1 / (k + rank_dense)
        rrf_k = 60
        rrf_scores = {}

        for rank, idx in enumerate(bm25_ranked[:20]):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, idx in enumerate(dense_ranked[:20]):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1.0 / (rrf_k + rank + 1))

        # Sort by combined RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)
        
        results = []
        for idx in sorted_indices[:top_k]:
            chunk_data = self.chunks[idx].copy()
            chunk_data["score"] = float(rrf_scores[idx])
            chunk_data["dense_score"] = float(dense_scores[idx])
            chunk_data["bm25_score"] = float(bm25_scores[idx])
            results.append(chunk_data)

        return results


# Global singleton instance
rag_retriever = HybridRAGRetriever()
