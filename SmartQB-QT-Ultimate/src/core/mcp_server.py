import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
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

_hybrid_engine = None

def get_engine():
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine()
    return _hybrid_engine

@server.tool()
async def sqb_hybrid_search(query: str, max_results: int = 5) -> str:
    """
    Triggers Dual Hybrid Search (LanceDB Dense + BM25 Sparse) to find exact questions.
    """
    try:
        engine = get_engine()
        results = engine.hybrid_search(query, top_k=max_results)
        return str(results)
    except Exception as e:
        return f"Search Error: {str(e)}"

@server.tool()
async def sqb_get_config_value(key: str) -> str:
    """
    Executes a safe read-only query on the configuration database.
    """
    from src.database.config_manager import ConfigManager
    import pathlib
    import os
    config_path = os.environ.get("SMARTQB_CONFIG_PATH", str(pathlib.Path(__file__).resolve().parent.parent.parent / "config.db"))
    try:
        cm = ConfigManager(str(config_path))
        # Master key setup is typically required here for decrypted reads,
        # For MCP tool context, we check if it requires decryption or return raw
        # (Assuming the app handles MasterKey setup elsewhere, we just retrieve)
        val = cm.get_value(key)
        return str(val) if val else "Key not found or not decrypted."
    except Exception as e:
        return f"Query Error: {str(e)}"

@server.tool()
async def sqb_generate_exam_sa(target_score: int, target_difficulty: float, tags: list[str]) -> str:
    """
    Calls the Simulated Annealing algorithm to generate an exam paper based on constraints.
    """
    try:
        assembler = ExamAssemblerSA(target_score, target_difficulty, {"tags": tags})
        engine = get_engine()
        table = engine._get_table()
        if not table:
            return "Generation Error: Question table is empty or does not exist."
        pool = table.search().limit(200).to_list()
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

if __name__ == "__main__":
    # Run as a standalone script using stdio transport for Claude Desktop integration
    import anyio
    import mcp.server.stdio

    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    anyio.run(main)
