from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import anyio

from ..models.db_manager import DatabaseManager
from ..services.prompt_manager import PromptManager
from ..services.db_selector import DBSelector
from ..services.sql_generator import SQLGenerator
from ..services.answer_generator import AnswerGenerator


router = APIRouter()


class QueryRequest(BaseModel):
  question: str


@router.post("/query")
async def query(req: QueryRequest) -> dict[str, Any]:
  from ..main import db_manager as dm
  from ..main import prompt_manager as pm
  from ..main import app_logger as logger

  selector = DBSelector(pm, dm)
  sqlgen = SQLGenerator(pm)
  ansg = AnswerGenerator(pm)

  db_name = await selector.choose_database(req.question)

  sql, base_prompt = await sqlgen.generate_sql(req.question, db_name)

  # run query in thread
  rows: list[dict]
  retried = False
  retry_error: str | None = None
  initial_error: str | None = None
  retry_sql_value: str | None = None
  try:
    rows = await anyio.to_thread.run_sync(lambda: dm.query(db_name, sql))
  except Exception as e:
    # retry once with error
    try:
      initial_error = str(e)
      retry_sql = await sqlgen.retry_with_error(base_prompt, initial_error)
      retry_sql_value = retry_sql
      rows = await anyio.to_thread.run_sync(lambda: dm.query(db_name, retry_sql))
      sql = retry_sql
      retried = True
    except Exception as e2:
      # final failure
      retry_error = str(e2)
      logger.log_query({
        "event": "query_failed",
        "question": req.question,
        "db": db_name,
        "sql": sql,
        "error": retry_error,
        "retry": {
          "initial_error": initial_error,
          "retry_sql": retry_sql_value,
          "retry_error": retry_error,
        },
      })
      raise HTTPException(status_code=400, detail={
        "message": "SQL 실행 실패",
        "error": retry_error,
        "sql": sql,
        "db": db_name,
      })

  answer = await ansg.generate(req.question, db_name, sql, rows)
  result = {
    "answer": answer,
    "used_db": db_name,
    "sql": sql,
    "rows": rows,
  }
  # log success
  payload = {
    "event": "query_succeeded",
    "question": req.question,
    "db": db_name,
    "sql": sql,
    "retried": retried,
    "answer": answer,
  }
  if retried:
    payload["retry"] = {
      "initial_error": initial_error,
      "retry_sql": retry_sql_value,
    }
  logger.log_query(payload)
  return result

