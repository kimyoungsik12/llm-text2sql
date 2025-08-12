from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from ..models.llm_client import LLMClient
from .prompt_manager import PromptManager


class AnswerGenerator:
  def __init__(self, prompt_manager: PromptManager) -> None:
    self.lm = LLMClient()
    self.pm = prompt_manager

  def _convert_dates_to_strings(self, obj):
    """날짜 타입과 Decimal 타입을 문자열로 변환하여 JSON 직렬화 가능하게 만듭니다."""
    if isinstance(obj, (date, datetime)):
      return str(obj)
    elif isinstance(obj, Decimal):
      return float(obj)  # Decimal을 float으로 변환
    elif isinstance(obj, dict):
      return {key: self._convert_dates_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
      return [self._convert_dates_to_strings(item) for item in obj]
    else:
      return obj

  async def generate(self, question: str, db_name: str, sql: str, rows: list[dict]) -> str:
    rules = self.pm.load_template("answer")
    preview_rows = rows[:50]  # guard
    
    # 날짜 타입을 문자열로 변환하여 JSON 직렬화 가능하게 만듭니다
    serializable_rows = self._convert_dates_to_strings(preview_rows)
    rows_json = json.dumps(serializable_rows, ensure_ascii=False)
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

