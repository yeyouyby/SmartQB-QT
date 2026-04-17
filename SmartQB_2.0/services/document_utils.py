import hashlib
import asyncio
import logging
import platform
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


from PySide6.QtCore import QStandardPaths


async def convert_docx_to_pdf(file_path: Path) -> Optional[Path]:
    """
    Converts DOCX to PDF silently via LibreOffice.
    Provides a graceful degradation if the conversion tool is missing.
    """
    cache_dir = (
        Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.CacheLocation
            )
        )
        / "pdf_previews"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    path_hash = hashlib.sha256(str(file_path.absolute()).encode()).hexdigest()[:32]
    pdf_path = cache_dir / f"{path_hash}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_mtime >= file_path.stat().st_mtime:
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

        with tempfile.TemporaryDirectory(prefix="smartqb_") as temp_dir:
            temp_outdir = Path(temp_dir)

            process = await asyncio.create_subprocess_exec(
                soffice_cmd,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_outdir),
                "--",
                str(file_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
            except asyncio.TimeoutError:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
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

            # Move the converted file from the unique temp dir back to the target directory
            temp_pdf_path = temp_outdir / file_path.with_suffix(".pdf").name
            if temp_pdf_path.exists():
                await asyncio.to_thread(shutil.copy2, temp_pdf_path, pdf_path)
                return pdf_path

        return None

    except Exception as e:
        logging.warning(
            f"Could not convert DOCX to PDF for UI preview. Skipping. Error: {e}"
        )
        return None
