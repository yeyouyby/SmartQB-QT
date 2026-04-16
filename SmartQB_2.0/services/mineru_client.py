import json
import logging
import httpx
import asyncio
from pathlib import Path
from typing import Dict, Any
from services.document_utils import convert_docx_to_pdf


class MinerUClient:
    MAX_POLLING_ATTEMPTS = 150
    POLLING_DELAY_SECONDS = 2

    """
    MinerU RESTful API Async Client.
    Executes tasks non-blockingly and generates local PDF for DOCX.
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/api/"):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(60.0, read=300.0, write=300.0),
        )

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Sends DOCX/PDF to MinerU and long-polls the task status.
        """
        # 1. Graceful DOCX to PDF Conversion
        if file_path.suffix.lower() == ".docx":
            pdf_path = await convert_docx_to_pdf(file_path)
            if pdf_path:
                file_path = pdf_path

        # 2. MinerU Submission
        file_content = await asyncio.to_thread(file_path.read_bytes)
        response = await self.client.post(
            "tasks", files={"file": (file_path.name, file_content)}
        )
        response.raise_for_status()
        try:
            response_data = response.json()
            if not isinstance(response_data, dict):
                raise ValueError(
                    f"Unexpected JSON response format from MinerU: {type(response_data)}"
                )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from MinerU: {e}")

        task_id = response_data.get("task_id")
        if not task_id:
            raise ValueError("Could not get task_id from MinerU response")

        # 3. Long Polling

        for _ in range(self.MAX_POLLING_ATTEMPTS):
            try:
                status_res = await self.client.get(f"tasks/{task_id}")
                status_res.raise_for_status()
                status_data = status_res.json()
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                if (
                    isinstance(e, httpx.HTTPStatusError)
                    and e.response.status_code < 500
                    and e.response.status_code != 429
                ):
                    raise
                # Handle transient network or parsing issues without aborting the entire process
                logging.warning(f"MinerU polling issue, retrying: {e}")
                await asyncio.sleep(self.POLLING_DELAY_SECONDS)
                continue

            if not isinstance(status_data, dict):
                logging.warning(
                    f"Unexpected status response format: {type(status_data)}"
                )
                await asyncio.sleep(self.POLLING_DELAY_SECONDS)
                continue

            status = status_data.get("status")
            if status == "SUCCESS":
                return status_data.get("result", {})
            elif status == "FAILED":
                error_msg = status_data.get("error", "Unknown error")
                raise RuntimeError(f"MinerU Task Failed: {error_msg}")
            elif status is None:
                logging.warning("MinerU response missing 'status' key, retrying...")

            await asyncio.sleep(self.POLLING_DELAY_SECONDS)

        raise TimeoutError("MinerU task timed out.")
