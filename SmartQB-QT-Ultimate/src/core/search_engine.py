import logging
import jieba
from typing import List, Dict
import lancedb
import sqlite3
import pathlib


class HybridSearchEngine:
    """
    Combines Dense Vector Retrieval (LanceDB) and Sparse Retrieval (SQLite FTS5 BM25)
    using Reciprocal Rank Fusion (RRF) for ultimate accuracy.
    """

    def __init__(self, db_path="./lancedb_store"):
        self.db = lancedb.connect(db_path)
        self.sqlite_path = (
            pathlib.Path(__file__).resolve().parent.parent.parent / "config.db"
        )

        # In a real app, this vectorizer would call OpenAI/BGE embeddings
        self._embedder = self._placeholder_embedder

    def _placeholder_embedder(self, query: str):
        logging.warning(
            "Using placeholder embedder; integrate real embedding service before production."
        )
        return [0.0] * 1536

    def get_table(self):
        if "questions" not in self.db.table_names():
            return None
        return self.db.open_table("questions")

    def bm25_search(self, query: str, top_k: int = 10) -> Dict[int, float]:
        """returns {question_id: rank} using SQLite FTS5"""
        try:
            ranks = {}
            with sqlite3.connect(str(self.sqlite_path)) as conn:
                cursor = conn.cursor()
                # Robust tokenization via jieba (Handles Chinese/Math boundaries)
                tokens = jieba.lcut(query.replace('"', ""))
                # Filter empties and construct MATCH query
                clean_tokens = [t.strip() for t in tokens if t.strip()]
                match_query = " OR ".join([f'"{q}"' for q in clean_tokens])
                cursor.execute(
                    "SELECT question_id, rank FROM questions_fts WHERE questions_fts MATCH ? ORDER BY rank LIMIT ?",
                    (match_query, top_k),
                )
                for i, row in enumerate(cursor.fetchall()):
                    q_id = int(row[0])
                    ranks[q_id] = i + 1
            return ranks
        except Exception as e:
            logging.error(f"FTS5 Search failed: {e}")
            return {}

    def dense_search(self, query: str, top_k: int = 10) -> Dict[int, int]:
        """returns {question_id: rank}"""
        table = self.get_table()
        if not table:
            return {}

        vector = self._embedder(query)
        results = table.search(vector).limit(top_k).to_list()

        ranks = {}
        for rank, res in enumerate(results):
            ranks[res["id"]] = rank + 1
        return ranks

    def hybrid_search(self, query: str, top_k: int = 10, rrf_k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion"""
        table = self.get_table()
        if not table:
            return []

        bm25_ranks = self.bm25_search(query, top_k=50)
        dense_ranks = self.dense_search(query, top_k=50)

        rrf_scores = {}
        all_ids = set(bm25_ranks.keys()).union(set(dense_ranks.keys()))

        for q_id in all_ids:
            score = 0.0
            if q_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[q_id])
            if q_id in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[q_id])
            rrf_scores[q_id] = score

        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        final_results = []
        for q_id, score in sorted_ids:
            try:
                # Query LanceDB directly for the specific hydrated ID
                # Parameterized LanceDB lookup to prevent formatting injection risks
                result = (
                    table.search().where("id = ?", parameters=[q_id]).limit(1).to_list()
                )
                if result:
                    q = result[0]
                    q["_rrf_score"] = score
                    final_results.append(q)
            except Exception:
                continue

        return final_results
