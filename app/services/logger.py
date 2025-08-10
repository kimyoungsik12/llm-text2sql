from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BASE_DIR / "logs"


class AppLogger:
  def __init__(self) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

  def _log_path_for_today(self) -> Path:
    day = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    return LOG_DIR / f"{day}.log"

  def log_query(self, payload: dict[str, Any]) -> None:
    # enrich with timestamp
    record = {
      "ts": datetime.now(timezone.utc).astimezone().isoformat(),
      **payload,
    }
    line = json.dumps(record, ensure_ascii=False)
    path = self._log_path_for_today()
    with path.open("a", encoding="utf-8") as f:
      f.write(line + "\n")

