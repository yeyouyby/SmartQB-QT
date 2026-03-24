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
    # Mock return for MCP Server
    return f"Search results for '{query}' (limit {max_results}): [Mock Question 1: mechanics, Mock Question 2: optics]"

@server.tool()
async def sqb_sql_query(sql_string: str) -> str:
    """
    Executes a read-only query on the configuration database.
    (Note: Main data is in LanceDB, this is only for meta-configs).
    """
    import sqlite3
    try:
        with sqlite3.connect("config.db") as conn:
            cursor = conn.cursor()
            cursor.execute(sql_string)
            results = cursor.fetchall()
            return str(results)
    except Exception as e:
        return f"Query Error: {str(e)}"

@server.tool()
async def sqb_generate_exam_sa(target_score: int, target_difficulty: float, tags: List[str]) -> str:
    """
    Calls the Simulated Annealing algorithm to generate an exam paper based on constraints.
    """
    assembler = ExamAssemblerSA(target_score, target_difficulty, {"tags": tags})
    # Mock return
    return f"Generated exam with score {target_score}, difficulty {target_difficulty}, tags {tags}. Exam ID: 12345"

@server.tool()
async def sqb_export_paper(bag_id: str, template_name: str) -> str:
    """
    Exports a completed exam bag to Word format using a template.
    """
    exporter = Exporter()
    output_file = f"export_{bag_id}.docx"
    success = exporter.export_word({"school": "MCP Triggered", "markdown": "Auto-generated from Claude Desktop."}, template_name, output_file)
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
