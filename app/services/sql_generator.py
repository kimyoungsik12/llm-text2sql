from __future__ import annotations

import re
from ..models.llm_client import LLMClient
from .prompt_manager import PromptManager


SQL_BLOCK_PATTERN = re.compile(r"```sql\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


class SQLGenerator:
  def __init__(self, prompt_manager: PromptManager) -> None:
    self.lm = LLMClient()
    self.pm = prompt_manager

  def _build_prompt(self, question: str, db_name: str) -> str:
    rules = self.pm.load_template("sql_generation", db_name=db_name)
    schema = self.pm.get_db_structure_prompt(db_name)
    return (
      f"{rules}\n\n"
      f"[DB 구조]\n{schema}\n\n"
      f"[요청]\n자연어 질문을 하나의 SQL 쿼리로 작성하세요.\n질문: {question}\n\n"
      f"출력 형식: SQL만 출력 (가능하면 ```sql 코드펜스```로 감싸기)")

  def _build_retry_prompt(self, base_prompt: str, error_message: str) -> str:
    return (
      f"{base_prompt}\n\n"
      f"[실패 원인]\n{error_message}\n\n"
      f"위 오류를 해결하도록 SQL을 수정하세요. 출력은 SQL만."
    )

  @staticmethod
  def _extract_sql(text: str) -> str:
    m = SQL_BLOCK_PATTERN.search(text)
    if m:
      sql = m.group(1).strip().rstrip(";") + ";"
    else:
      # no block, take first line/paragraph
      sql = text.strip()
      # strip surrounding backticks if any
      sql = sql.strip("`")
      # ensure ending semicolon for mysql compatibility
      if not sql.endswith(";"):
        sql += ";"
    
    # 개행문자 제거하고 한 줄로 만들기
    sql = sql.replace('\n', ' ').replace('\r', ' ')
    # 여러 개의 공백을 하나로 정리
    sql = ' '.join(sql.split())
    
    return sql

  async def generate_sql(self, question: str, db_name: str) -> tuple[str, str]:
    base_prompt = self._build_prompt(question, db_name)
    text = await self.lm.generate(base_prompt, temperature=0.0)
    sql = self._extract_sql(text)
    return sql, base_prompt

  async def retry_with_error(self, base_prompt: str, error_message: str) -> str:
    prompt = self._build_retry_prompt(base_prompt, error_message)
    text = await self.lm.generate(prompt, temperature=0.0)
    return self._extract_sql(text)

