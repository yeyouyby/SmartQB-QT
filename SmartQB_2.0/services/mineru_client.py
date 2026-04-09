import httpx
import asyncio
import logging
import platform
import os
from pathlib import Path
from typing import Dict, Any, Optional
import shutil


class MinerUClient:
    """
    MinerU RESTful API Async Client.
    Executes tasks non-blockingly and generates local PDF for DOCX.
    """

    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/api/"):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def close(self):
        await self.client.aclose()

    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Sends DOCX/PDF to MinerU and long-polls the task status.
        """
        # 1. Graceful DOCX to PDF Conversion
        if file_path.suffix.lower() == ".docx":
            pdf_path = await self._convert_docx_to_pdf(file_path)
            if pdf_path:
                file_path = pdf_path
            # 2. MinerU Submission
        file_content = await asyncio.to_thread(file_path.read_bytes)
        response = await self.client.post(
            "tasks", files={"file": (file_path.name, file_content)}
        )
        response.raise_for_status()
        task_id = response.json().get("task_id")

        # 3. Long Polling
        max_retries = 150
        for _ in range(max_retries):
            status_res = await self.client.get(f"tasks/{task_id}")
            status_res.raise_for_status()
            status_data = status_res.json()

            if status_data.get("status") == "SUCCESS":
                return status_data.get("result", {})
            elif status_data.get("status") == "FAILED":
                raise RuntimeError(f"MinerU Task Failed: {status_data.get('error')}")

            await asyncio.sleep(2)

        raise TimeoutError("MinerU task timed out.")

    async def _convert_docx_to_pdf(self, file_path: Path) -> Optional[Path]:
        """
        Converts DOCX to PDF silently via LibreOffice or docx2pdf.
        Provides a graceful degradation if the conversion tool is missing.
        """
        pdf_path = file_path.with_suffix(".pdf")
        if pdf_path.exists():
            return pdf_path

        try:
            # LibreOffice headless approach for CI/Linux
            soffice_cmd = shutil.which("soffice")
            if not soffice_cmd:
                system = platform.system()
                if system == "Windows":
                    # Check both 64-bit and 32-bit program files directories
                    possible_paths = []
                    for env_var in ("ProgramFiles", "ProgramFiles(x86)"):
                        program_files = os.environ.get(env_var)
                        if program_files:
                            possible_paths.append(
                                Path(program_files) / "LibreOffice/program/soffice.exe"
                            )
                    for path in possible_paths:
                        if path.exists():
                            soffice_cmd = str(path)
                            break
                elif system == "Darwin":
                    mac_path = Path(
                        "/Applications/LibreOffice.app/Contents/MacOS/soffice"
                    )
                    if mac_path.exists():
                        soffice_cmd = str(mac_path)

            if not soffice_cmd:
                raise FileNotFoundError(
                    "soffice executable not found in PATH or standard locations."
                )

            process = await asyncio.create_subprocess_exec(
                soffice_cmd,
                "--headless",
                "--convert-to",
                "pdf",
                str(file_path),
                "--outdir",
                str(file_path.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise

            if process.returncode != 0:
                error_output = (
                    stderr.decode("utf-8", errors="ignore")
                    if stderr
                    else "No error output."
                )
                raise RuntimeError(
                    f"LibreOffice conversion failed with return code {process.returncode}. Error: {error_output}"
                )

            return pdf_path

        except Exception as e:
            logging.warning(
                f"Could not convert DOCX to PDF for UI preview. Skipping. Error: {e}"
            )
            return None
