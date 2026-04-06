import httpx
import asyncio
import anyio
import logging
from pathlib import Path
from typing import Dict, Any


class MinerUClient:
    """
    MinerU RESTful API Async Client.
    Executes tasks non-blockingly and generates local PDF for DOCX.
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/api"):
        self.client = httpx.AsyncClient(
            base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def close(self):
        await self.client.aclose()

    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Sends DOCX/PDF to MinerU and long-polls the task status.
        """
        # 1. Graceful DOCX to PDF Conversion
        if file_path.suffix.lower() == ".docx":
            file_path = await self._convert_docx_to_pdf(file_path)
            if file_path is None or file_path.suffix.lower() != ".pdf":
                raise FileNotFoundError("Could not convert DOCX to PDF for UI preview.")

            # 2. MinerU Submission
        async with await anyio.open_file(file_path, "rb") as f:
            response = await self.client.post(
                "/tasks", files={"file": (file_path.name, f)}
            )
        response.raise_for_status()
        task_id = response.json().get("task_id")

        # 3. Long Polling
        max_retries = 150  # Increased to 300 seconds
        for _ in range(max_retries):
            status_res = await self.client.get(f"/tasks/{task_id}")
            status_res.raise_for_status()
            status_data = status_res.json()

            if status_data.get("status") == "SUCCESS":
                return status_data.get("result", {})
            elif status_data.get("status") == "FAILED":
                raise RuntimeError(f"MinerU Task Failed: {status_data.get('error')}")

            await asyncio.sleep(2)

        raise TimeoutError("MinerU task timed out after 300 seconds.")

    async def _convert_docx_to_pdf(self, file_path: Path) -> Path:
        """
        Converts DOCX to PDF silently via LibreOffice or docx2pdf.
        Provides a graceful degradation if the conversion tool is missing.
        """
        pdf_path = file_path.with_suffix(".pdf")
        if pdf_path.exists():
            return pdf_path

        try:
            # LibreOffice headless approach for CI/Linux
            process = await asyncio.create_subprocess_exec(  # nosec B603 B607
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                str(file_path),
                "--outdir",
                str(file_path.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if process.returncode != 0:
                raise FileNotFoundError("LibreOffice conversion failed or not found.")

            return pdf_path

        except Exception as e:
            logging.warning(
                f"Could not convert DOCX to PDF for UI preview. Skipping. Error: {e}"
            )
            return file_path
