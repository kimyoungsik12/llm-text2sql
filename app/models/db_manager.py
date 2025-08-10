from __future__ import annotations

import mysql.connector
from mysql.connector import pooling
from typing import Any
import yaml
from pathlib import Path
from ..config import settings


class DatabaseConfig:
  def __init__(self, name: str, host: str, port: int, user: str, password: str, database: str, description: str | None = None) -> None:
    self.name = name
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.database = database
    self.description = description or name


class DatabaseManager:
  def __init__(self) -> None:
    self.databases: list[DatabaseConfig] = []
    self.pools: dict[str, pooling.MySQLConnectionPool] = {}

  def load_config(self) -> None:
    yaml_path = Path(settings.databases_yaml_path)
    if not yaml_path.exists():
      raise FileNotFoundError(f"Databases config not found: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    self.databases = []
    for item in data.get("databases", []):
      cfg = DatabaseConfig(
        name=item["name"],
        host=item.get("host", "127.0.0.1"),
        port=int(item.get("port", 3306)),
        user=item.get("user", "root"),
        password=item.get("password", ""),
        database=item.get("database", item["name"]),
        description=item.get("description"),
      )
      self.databases.append(cfg)

  def connect_all(self) -> None:
    self.pools = {}
    for cfg in self.databases:
      pool = pooling.MySQLConnectionPool(
        pool_name=f"pool_{cfg.name}", pool_size=5, host=cfg.host, port=cfg.port,
        user=cfg.user, password=cfg.password, database=cfg.database
      )
      self.pools[cfg.name] = pool

  def close_all(self) -> None:
    self.pools = {}

  def list_db_names(self) -> list[str]:
    return [d.name for d in self.databases]

  def get_db_description(self, name: str) -> str:
    for d in self.databases:
      if d.name == name:
        return d.description
    return name

  def get_connection(self, db_name: str):
    if db_name not in self.pools:
      raise KeyError(f"Unknown DB: {db_name}")
    return self.pools[db_name].get_connection()

  def query(self, db_name: str, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    conn = self.get_connection(db_name)
    try:
      cur = conn.cursor(dictionary=True)
      cur.execute(sql, params or ())
      rows = cur.fetchall()
      return rows
    finally:
      try:
        cur.close()
      except Exception:
        pass
      conn.close()

  def get_schema_text(self, db_name: str) -> str:
    conn = self.get_connection(db_name)
    try:
      cur = conn.cursor()
      cur.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
      )
      columns = cur.fetchall()

      cur.execute(
        """
        SELECT
          kcu.TABLE_NAME,
          kcu.COLUMN_NAME,
          kcu.REFERENCED_TABLE_NAME,
          kcu.REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
        WHERE kcu.TABLE_SCHEMA = DATABASE()
          AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
        """
      )
      fks = cur.fetchall()
    finally:
      try:
        cur.close()
      except Exception:
        pass
      conn.close()

    # format
    lines: list[str] = []
    lines.append(f"# DB: {db_name}")
    lines.append("## Tables and Columns")
    last_table = None
    for tbl, col, dtype, is_null, col_key in columns:
      if tbl != last_table:
        lines.append("")
        lines.append(f"- Table: {tbl}")
        last_table = tbl
      key = f" [{col_key}]" if col_key else ""
      lines.append(f"  - {col}: {dtype} NULLABLE={is_null}{key}")

    lines.append("")
    lines.append("## Foreign Keys")
    for tbl, col, rt, rc in fks:
      lines.append(f"- {tbl}.{col} -> {rt}.{rc}")

    return "\n".join(lines)

