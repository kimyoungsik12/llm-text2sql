from __future__ import annotations

from pathlib import Path
from typing import Optional
from ..models.db_manager import DatabaseManager


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "prompts" / "templates"
GENERATED_DIR = BASE_DIR / "prompts" / "generated"


class PromptManager:
  def ensure_directories(self) -> None:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

  def generate_db_structure_prompts(self, db_manager: DatabaseManager) -> None:
    for db in db_manager.list_db_names():
      out_path = GENERATED_DIR / f"{db}__db_structure.txt"
      try:
        schema_text = db_manager.get_schema_text(db)
        out_path.write_text(schema_text, encoding="utf-8")
      except Exception as e:
        # 연결 불가 시 안내 문서만 생성하고 넘어감
        out_path.write_text(
          f"# DB: {db}\n연결 실패로 스키마를 가져오지 못했습니다. 서버 설정과 DB 상태를 확인하세요.\n에러: {e}",
          encoding="utf-8",
        )

  def load_template(self, name: str, db_name: Optional[str] = None) -> str:
    # Allow per-DB override: name__{db}.txt
    if db_name:
      cand = TEMPLATES_DIR / f"{name}__{db_name}.txt"
      if cand.exists():
        return cand.read_text(encoding="utf-8")
    # Fallback to common
    path = TEMPLATES_DIR / f"{name}.txt"
    if not path.exists():
      return ""
    return path.read_text(encoding="utf-8")

  def load_generated(self, filename: str) -> str:
    path = GENERATED_DIR / filename
    if not path.exists():
      return ""
    return path.read_text(encoding="utf-8")

  def get_db_structure_prompt(self, db_name: str) -> str:
    return self.load_generated(f"{db_name}__db_structure.txt")

