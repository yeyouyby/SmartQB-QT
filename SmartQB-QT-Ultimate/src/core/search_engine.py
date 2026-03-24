from typing import List, Dict, Any
import lancedb
from rank_bm25 import BM25Okapi
import numpy as np

class HybridSearchEngine:
    """
    Combines Dense Vector Retrieval (LanceDB) and Sparse Retrieval (BM25)
    using Reciprocal Rank Fusion (RRF) for ultimate accuracy.
    """
    def __init__(self, db_path="./lancedb_store"):
        self.db = lancedb.connect(db_path)
        # In a real app, this vectorizer would call OpenAI/BGE embeddings
        # For now, we simulate embedding function
        self._embedder = lambda x: [0.0] * 1536

    def _get_table(self):
        if "questions" not in self.db.table_names():
            return None
        return self.db.open_table("questions")

    def bm25_search(self, query: str, questions: List[Dict], top_k: int = 10) -> Dict[int, int]:
        """ returns {question_id: rank} """
        if not questions:
            return {}

        tokenized_corpus = [q["content_md"].split(" ") for q in questions]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split(" ")

        scores = bm25.get_scores(tokenized_query)
        # Get indices sorted by score descending
        top_indices = np.argsort(scores)[::-1][:top_k]

        ranks = {}
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0: # Only keep positive matches
                q_id = questions[idx]["id"]
                ranks[q_id] = rank + 1
        return ranks

    def dense_search(self, query: str, top_k: int = 10) -> Dict[int, int]:
        """ returns {question_id: rank} """
        table = self._get_table()
        if not table:
            return {}

        vector = self._embedder(query)
        # LanceDB Search
        results = table.search(vector).limit(top_k).to_list()

        ranks = {}
        for rank, res in enumerate(results):
            ranks[res["id"]] = rank + 1
        return ranks

    def hybrid_search(self, query: str, top_k: int = 10, rrf_k: int = 60) -> List[Dict]:
        """ Reciprocal Rank Fusion """
        table = self._get_table()
        if not table:
            return []

        # Fetch all questions for BM25 local corpus (in prod, use Tantivy/Elasticsearch for huge datasets)
        all_questions = table.search().limit(1000).to_list()

        bm25_ranks = self.bm25_search(query, all_questions, top_k=50)
        dense_ranks = self.dense_search(query, top_k=50)

        # RRF Fusion
        rrf_scores = {}
        all_ids = set(bm25_ranks.keys()).union(set(dense_ranks.keys()))

        for q_id in all_ids:
            score = 0.0
            if q_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[q_id])
            if q_id in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[q_id])
            rrf_scores[q_id] = score

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Hydrate results
        final_results = []
        id_to_q = {q["id"]: q for q in all_questions}
        for q_id, score in sorted_ids:
            if q_id in id_to_q:
                q = id_to_q[q_id]
                q["_rrf_score"] = score
                final_results.append(q)

        return final_results
