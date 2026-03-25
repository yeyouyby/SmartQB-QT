# 8. core/mcp_server.py
with open('src/core/mcp_server.py', 'r') as f: content = f.read()

mcp_hybrid = """@server.tool()
async def sqb_hybrid_search(query: str, max_results: int = 5) -> str:
    \"\"\"
    Triggers Dual Hybrid Search (LanceDB Dense + BM25 Sparse) to find exact questions.
    \"\"\"
    engine = HybridSearchEngine()
    # Mock return for MCP Server
    return f"Search results for '{query}' (limit {max_results}): [Mock Question 1: mechanics, Mock Question 2: optics]\""""

mcp_hybrid_new = """@server.tool()
async def sqb_hybrid_search(query: str, max_results: int = 5) -> str:
    \"\"\"
    Triggers Dual Hybrid Search (LanceDB Dense + BM25 Sparse) to find exact questions.
    \"\"\"
    engine = HybridSearchEngine()
    try:
        results = engine.hybrid_search(query, top_k=max_results)
        return str(results)
    except Exception as e:
        return f"Search Error: {str(e)}\""""
content = content.replace(mcp_hybrid, mcp_hybrid_new)

mcp_gen = """@server.tool()
async def sqb_generate_exam_sa(target_score: int, target_difficulty: float, tags: List[str]) -> str:
    \"\"\"
    Calls the Simulated Annealing algorithm to generate an exam paper based on constraints.
    \"\"\"
    assembler = ExamAssemblerSA(target_score, target_difficulty, {"tags": tags})
    # Mock return
    return f"Generated exam with score {target_score}, difficulty {target_difficulty}, tags {tags}. Exam ID: 12345\""""

mcp_gen_new = """@server.tool()
async def sqb_generate_exam_sa(target_score: int, target_difficulty: float, tags: List[str]) -> str:
    \"\"\"
    Calls the Simulated Annealing algorithm to generate an exam paper based on constraints.
    \"\"\"
    try:
        assembler = ExamAssemblerSA(target_score, target_difficulty, {"tags": tags})
        engine = HybridSearchEngine()
        pool = engine.db.open_table("questions").search().limit(200).to_list()
        paper = assembler.assemble(pool, max_size=20)
        return f"Generated Exam Paper with {len(paper)} questions."
    except Exception as e:
        return f"Generation Error: {str(e)}\""""
content = content.replace(mcp_gen, mcp_gen_new)

mcp_export = """@server.tool()
async def sqb_export_paper(bag_id: str, template_name: str) -> str:
    \"\"\"
    Exports a completed exam bag to Word format using a template.
    \"\"\"
    exporter = Exporter()
    output_file = f"export_{bag_id}.docx"
    success = exporter.export_word({"school": "MCP Triggered", "markdown": "Auto-generated from Claude Desktop."}, template_name, output_file)
    if success:
        return f"Successfully exported to {output_file}"
    return "Export Failed\""""

mcp_export_new = """@server.tool()
async def sqb_export_paper(bag_id: str, template_name: str) -> str:
    \"\"\"
    Exports a completed exam bag to Word format using a template.
    \"\"\"
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
    return "Export Failed\""""
content = content.replace(mcp_export, mcp_export_new)

mcp_sql = """@server.tool()
async def sqb_sql_query(sql_string: str) -> str:
    \"\"\"
    Executes a read-only query on the configuration database.
    (Note: Main data is in LanceDB, this is only for meta-configs).
    \"\"\"
    import sqlite3
    try:
        with sqlite3.connect("config.db") as conn:
            cursor = conn.cursor()
            cursor.execute(sql_string)
            results = cursor.fetchall()
            return str(results)
    except Exception as e:
        return f"Query Error: {str(e)}\""""

mcp_sql_new = """@server.tool()
async def sqb_get_config_value(key: str) -> str:
    \"\"\"
    Executes a safe read-only query on the configuration database.
    \"\"\"
    import sqlite3
    try:
        with sqlite3.connect("config.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
            results = cursor.fetchone()
            return str(results)
    except Exception as e:
        return f"Query Error: {str(e)}\""""
content = content.replace(mcp_sql, mcp_sql_new)

with open('src/core/mcp_server.py', 'w') as f: f.write(content)
