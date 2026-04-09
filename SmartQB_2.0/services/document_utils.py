import asyncio
import logging
import platform
import os
import shutil
from pathlib import Path
from typing import Optional


async def convert_docx_to_pdf(file_path: Path) -> Optional[Path]:
    """
    Converts DOCX to PDF silently via LibreOffice.
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
                mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
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
