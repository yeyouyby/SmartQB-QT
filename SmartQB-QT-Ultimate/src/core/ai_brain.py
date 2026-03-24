import openai
from PySide6.QtCore import QThread, Signal
from typing import Optional
from src.database.config_manager import ConfigManager
import json

class AIBrain:
    """
    Core wrapper for OpenAI-compatible APIs (like DeepSeek, Kimi, GLM).
    Handles API setup using the secure ConfigManager.
    """
    def __init__(self, db_path="config.db"):
        self.cm = ConfigManager(db_path)
        # Assuming Master Key is loaded in main app. If not, this might fail or return None.
        try:
            self.api_key = self.cm.get_value("openai_api_key")
            self.base_url = self.cm.get_value("openai_base_url", "https://api.openai.com/v1")
            self.model = self.cm.get_value("openai_model", "gpt-3.5-turbo")

            if self.api_key:
                self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                self.client = None
        except ValueError:
            self.client = None

    def _ensure_client(self):
        if not self.client:
            raise ValueError("AI Client not initialized. Please set API Key and Master Key in settings.")

    def correct_markdown(self, raw_md: str) -> str:
        """ AI Text correction & LaTeX formatting """
        self._ensure_client()
        system_prompt = (
            "You are an expert Math & Physics OCR corrector. "
            "Fix broken Markdown and ensure all math formulas are correctly formatted using MathJax ($$)."
            "Output ONLY the corrected markdown. Do not add conversational text."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_md}
            ]
        )
        return response.choices[0].message.content

    def expand_query(self, user_query: str) -> str:
        """ Expand a simple query into rich keywords for Hybrid Search """
        self._ensure_client()
        prompt = f"Expand this educational query into 5 comma-separated exact keywords/concepts for vector search: '{user_query}'. Return ONLY the keywords."
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

class AICorrectionWorker(QThread):
    """
    QThread for performing AI correction asynchronously to prevent UI freeze.
    """
    result_ready = Signal(str)
    error = Signal(str)

    def __init__(self, raw_text: str):
        super().__init__()
        self.raw_text = raw_text

    def run(self):
        try:
            brain = AIBrain()
            # If API is missing, simulate for now to avoid crashing testing UI
            if not brain.client:
                import time
                time.sleep(1.5)
                corrected = f"✅ [Simulated Corrected via AI]\n\n{self.raw_text}\n\n$$E = mc^2$$"
            else:
                corrected = brain.correct_markdown(self.raw_text)
            self.result_ready.emit(corrected)
        except Exception as e:
            self.error.emit(f"AI Error: {str(e)}")
