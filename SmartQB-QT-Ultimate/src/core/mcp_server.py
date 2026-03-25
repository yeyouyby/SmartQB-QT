import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import threading
import logging
from mcp import Server
import sys

app = FastAPI(title="SmartQB MCP Server")
server = Server("smartqb-mcp")

# --- Dependencies ---
from .search_engine import HybridSearchEngine
from .assembly import ExamAssemblerSA
from .export import Exporter

class QueryRequest(BaseModel):
    query: str
    max_results: int = 5

class ConstraintsRequest(BaseModel):
    target_score: int
    target_difficulty: float
    tags: List[str]

@server.tool()
async def sqb_hybrid_search(query: str, max_results: int = 5) -> str:
    """
    Triggers Dual Hybrid Search (LanceDB Dense + BM25 Sparse) to find exact questions.
    """
    engine = HybridSearchEngine()
    try:
        results = engine.hybrid_search(query, top_k=max_results)
        return str(results)
    except Exception as e:
        return f"Search Error: {str(e)}"

@server.tool()
async def sqb_get_config_value(key: str) -> str:
    """
    Executes a safe read-only query on the configuration database.
    """
    import sqlite3
    try:
        with sqlite3.connect("config.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
            results = cursor.fetchone()
            return str(results)
    except Exception as e:
        return f"Query Error: {str(e)}"

@server.tool()
async def sqb_generate_exam_sa(target_score: int, target_difficulty: float, tags: List[str]) -> str:
    """
    Calls the Simulated Annealing algorithm to generate an exam paper based on constraints.
    """
    try:
        assembler = ExamAssemblerSA(target_score, target_difficulty, {"tags": tags})
        engine = HybridSearchEngine()
        pool = engine.db.open_table("questions").search().limit(200).to_list()
        paper = assembler.assemble(pool, max_size=20)
        return f"Generated Exam Paper with {len(paper)} questions."
    except Exception as e:
        return f"Generation Error: {str(e)}"

@server.tool()
async def sqb_export_paper(bag_id: str, template_name: str) -> str:
    """
    Exports a completed exam bag to Word format using a template.
    """
    import re
    from werkzeug.utils import secure_filename

    clean_bag_id = secure_filename(bag_id)
    if not clean_bag_id:
        return "Invalid bag_id"
    clean_template = secure_filename(template_name)
    if not clean_template:
        return "Invalid template_name"

    exporter = Exporter()
    output_file = f"export_{clean_bag_id}.docx"
    success = exporter.export_word({"school": "MCP Triggered", "markdown": "Auto-generated from Claude Desktop."}, clean_template, output_file)
    if success:
        return f"Successfully exported to {output_file}"
    return "Export Failed"

def start_mcp_server_bg():
    """
    Starts the FastMCP/SSE server in a daemon thread so it runs alongside the PySide6 app.
    """
    def _run():
        logging.info("Starting background MCP Server on port 8000...")
        import anyio
        # Run using an SSE server or direct FastMCP bindings depending on library version
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    start_mcp_server_bg()
    import time
    time.sleep(10)
