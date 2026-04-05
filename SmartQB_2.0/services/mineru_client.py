import httpx
import asyncio
import subprocess
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
            pdf_preview_path = await self._convert_docx_to_pdf(file_path)

        # 2. MinerU Submission (Intentionally passing original file, NOT the PDF)
        file_content = await asyncio.to_thread(file_path.read_bytes)
        response = await self.client.post(
            "/tasks", files={"file": (file_path.name, file_content)}
        )
        response.raise_for_status()
        task_id = response.json().get("task_id")
        if not task_id:
            raise RuntimeError(f"Failed to get task_id from MinerU: {response.text}")

        # 3. Long Polling
        max_retries = 90  # Increased to 180 seconds
        for _ in range(max_retries):
            status_res = await self.client.get(f"/tasks/{task_id}")
            status_res.raise_for_status()
            status_data = status_res.json()

            if status_data.get("status") == "SUCCESS":
                result_data = status_data.get("result", {})
                if file_path.suffix.lower() == ".docx":
                    result_data["pdf_preview_path"] = str(pdf_preview_path)
                return result_data
            elif status_data.get("status") == "FAILED":
                error_msg = status_data.get("error", "Unknown error")
                raise RuntimeError(f"MinerU Task Failed: {error_msg}")

            await asyncio.sleep(2)

        raise TimeoutError("MinerU task timed out.")

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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
