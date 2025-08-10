from __future__ import annotations

import json
from ..models.llm_client import LLMClient
from .prompt_manager import PromptManager


class AnswerGenerator:
  def __init__(self, prompt_manager: PromptManager) -> None:
    self.lm = LLMClient()
    self.pm = prompt_manager

  async def generate(self, question: str, db_name: str, sql: str, rows: list[dict]) -> str:
    rules = self.pm.load_template("answer")
    preview_rows = rows[:50]  # guard
    rows_json = json.dumps(preview_rows, ensure_ascii=False)
    prompt = (
      f"{rules}\n\n"
      f"[질문]\n{question}\n\n"
      f"[사용 DB]\n{db_name}\n\n"
      f"[생성된 SQL]\n{sql}\n\n"
      f"[쿼리 결과 샘플]\n{rows_json}\n\n"
      f"출력 형식: 사용자에게 보여줄 한국어 답변만 출력"
    )
    text = await self.lm.generate(prompt, temperature=0.2)
    return text.strip()

