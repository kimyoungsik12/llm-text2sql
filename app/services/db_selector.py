from __future__ import annotations

from ..models.llm_client import LLMClient
from ..models.db_manager import DatabaseManager
from .prompt_manager import PromptManager


class DBSelector:
  def __init__(self, prompt_manager: PromptManager, db_manager: DatabaseManager) -> None:
    self.lm = LLMClient()
    self.pm = prompt_manager
    self.dbs = db_manager

  async def choose_database(self, question: str) -> str:
    names = self.dbs.list_db_names()
    if len(names) == 1:
      return names[0]
    rules = self.pm.load_template("db_selection")
    options_lines = []
    for n in names:
      desc = self.dbs.get_db_description(n)
      options_lines.append(f"- {n}: {desc}")
    options = "\n".join(options_lines)
    prompt = (
      f"{rules}\n\n"
      f"질문:\n{question}\n\n"
      f"DB 후보:\n{options}\n\n"
      f"출력 형식: 선택한 DB의 이름만 단일 라인으로 출력"
    )
    text = await self.lm.generate(prompt, temperature=0.0)
    chosen = text.strip().splitlines()[0].strip()
    # Normalize to known names
    for n in names:
      if n.lower() == chosen.lower():
        return n
    # fallback: first db
    return names[0]

