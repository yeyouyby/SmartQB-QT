import queue
import multiprocessing as mp
from PySide6.QtCore import QThread, Signal
from typing import Dict, Any, List
from .parser import PPStructureParser
import logging
import json
import uuid
import os
import tempfile


class OCRWorker(QThread):
    """
    Handles heavy OCR tasks asynchronously without blocking the PySide6 UI loop.
    Uses QThread to manage multiprocessing calls.
    """

    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    @staticmethod
    def _run_ocr_process(file_path: str, result_queue: mp.Queue):
        """Runs in an isolated multiprocessing process to prevent GIL blocking."""
        try:
            parser = PPStructureParser()
            result = parser.parse(file_path)

            # Serialize result to a temporary JSON file to avoid memory explosion & IPC queue limits
            temp_path = os.path.join(
                tempfile.gettempdir(), f"ocr_result_{uuid.uuid4().hex}.json"
            )
            with open(temp_path, "w", encoding="utf-8") as tf:
                json.dump(result, tf)

            result_queue.put({"status": "success", "data_file": temp_path})
        except Exception as e:
            result_queue.put({"status": "error", "message": str(e)})

    def run(self):
        """Called when thread.start() is invoked."""
        try:
            self.progress.emit(10)
            result_queue = mp.Queue()

            # Start process
            p = mp.Process(
                target=self._run_ocr_process, args=(self.file_path, result_queue)
            )
            p.start()

            # Simulate progress while process runs
            import time

            prog = 10
            while p.is_alive():
                prog = min(99, prog + 5)
                self.progress.emit(prog)
                time.sleep(0.1)

            p.join()
            self.progress.emit(100)

            try:
                result = result_queue.get(timeout=30)
                if result["status"] == "success":
                    data_file = result["data_file"]
                    with open(data_file, "r", encoding="utf-8") as df:
                        parsed_data = json.load(df)
                    self.finished.emit(parsed_data)
                    os.remove(data_file)
                else:
                    self.error.emit(result["message"])

            except queue.Empty:
                self.error.emit(
                    f"OCR Process Timeout: subprocess did not return data. Exit code: {p.exitcode}"
                )
        except Exception as e:
            self.error.emit(str(e))


class DatabaseWorker(QThread):
    """
    Handles background database operations (LanceDB search/insert, SQLite operations).
    """

    result_ready = Signal(object)
    error = Signal(str)

    def __init__(self, operation_func, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.operation_func(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))


if __name__ == "__main__":
    logging.info("Concurrency layer loaded.")
