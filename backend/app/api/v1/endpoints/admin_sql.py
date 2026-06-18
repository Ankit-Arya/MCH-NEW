from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import MASTER_ADMIN_ROLES, require_roles
from app.models.all_models import User
from app.services.audit_service import audit_log

router = APIRouter()

READONLY_DATABASE_URL = os.getenv("READONLY_DATABASE_URL")
ADMIN_SQL_MAX_ROWS = int(os.getenv("ADMIN_SQL_MAX_ROWS", "1000"))
ADMIN_SQL_TIMEOUT_MS = int(os.getenv("ADMIN_SQL_TIMEOUT_MS", "8000"))

_readonly_engine: Engine | None = (
    create_engine(READONLY_DATABASE_URL, pool_pre_ping=True, pool_size=2, max_overflow=3)
    if READONLY_DATABASE_URL
    else None
)

ALLOWED_START = ("SELECT", "WITH", "SHOW", "EXPLAIN")

BLOCKED_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "DO",
    "EXECUTE",
    "MERGE",
    "REFRESH",
    "REINDEX",
    "CLUSTER",
    "VACUUM",
    "ANALYZE",
    "SET",
    "RESET",
    "LISTEN",
    "NOTIFY",
)

BLOCKED_PATTERNS = (
    r"\bFOR\s+UPDATE\b",
    r"\bFOR\s+SHARE\b",
    r"\bFOR\s+KEY\s+SHARE\b",
    r"\bFOR\s+NO\s+KEY\s+UPDATE\b",
    r"\bPG_SLEEP\s*\(",
    r"\bNEXTVAL\s*\(",
    r"\bSETVAL\s*\(",
)


class AdminSqlExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=20000)
    limit: int = Field(default=100, ge=1, le=5000)


class AdminSqlExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool
    duration_ms: int


def _require_admin_sql_access(user: User) -> None:
    require_roles(user, MASTER_ADMIN_ROLES)


def _engine() -> Engine:
    if _readonly_engine is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="READONLY_DATABASE_URL is not configured for Admin SQL Tool.",
        )
    return _readonly_engine


def _validate_readonly_sql(sql: str) -> str:
    cleaned = sql.strip()

    if not cleaned:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    # Allow one trailing semicolon, but block multiple statements.
    cleaned = cleaned.rstrip(";").strip()

    if ";" in cleaned:
        raise HTTPException(status_code=400, detail="Only one SQL statement is allowed.")

    upper_sql = cleaned.upper()

    if not upper_sql.startswith(ALLOWED_START):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT, WITH, SHOW and safe EXPLAIN queries are allowed.",
        )

    for word in BLOCKED_WORDS:
        if re.search(rf"\b{word}\b", upper_sql):
            raise HTTPException(status_code=400, detail=f"Blocked SQL keyword: {word}")

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, upper_sql):
            raise HTTPException(status_code=400, detail="This SQL pattern is not allowed.")

    return cleaned


def _serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    return value


def _serialize_row(row) -> dict:
    return {key: _serialize_value(value) for key, value in dict(row).items()}


def _audit_sql(db: Session, user: User, *, query_text: str, success: bool, row_count: int, duration_ms: int, error: str | None = None) -> None:
    try:
        audit_log(
            db,
            actor=user,
            action="ADMIN_SQL_EXECUTED" if success else "ADMIN_SQL_FAILED",
            entity_type="AdminSql",
            new_value={
                "query_preview": query_text[:500],
                "success": success,
                "row_count": row_count,
                "duration_ms": duration_ms,
                "error": error[:500] if error else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()


@router.post("/execute", response_model=AdminSqlExecuteResponse)
def execute_admin_sql(
    payload: AdminSqlExecuteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin_sql_access(user)

    sql = _validate_readonly_sql(payload.sql)
    max_rows = min(payload.limit, ADMIN_SQL_MAX_ROWS)
    timeout_ms = min(ADMIN_SQL_TIMEOUT_MS, 30000)
    started = time.perf_counter()

    try:
        with _engine().connect() as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))

                result = conn.execute(text(sql))

                if not result.returns_rows:
                    columns = []
                    rows = []
                    truncated = False
                else:
                    fetched = result.mappings().fetchmany(max_rows + 1)
                    truncated = len(fetched) > max_rows
                    fetched = fetched[:max_rows]
                    columns = list(result.keys())
                    rows = [_serialize_row(row) for row in fetched]

        duration_ms = int((time.perf_counter() - started) * 1000)
        _audit_sql(db, user, query_text=sql, success=True, row_count=len(rows), duration_ms=duration_ms)

        return AdminSqlExecuteResponse(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=duration_ms,
        )

    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _audit_sql(db, user, query_text=sql, success=False, row_count=0, duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {str(exc)}")


@router.get("/tables")
def list_admin_sql_tables(user: User = Depends(get_current_user)):
    _require_admin_sql_access(user)

    query = """
        SELECT
            table_schema,
            table_name,
            table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """

    with _engine().connect() as conn:
        result = conn.execute(text(query))
        return [dict(row) for row in result.mappings().all()]


@router.get("/columns")
def list_admin_sql_columns(
    table_schema: str,
    table_name: str,
    user: User = Depends(get_current_user),
):
    _require_admin_sql_access(user)

    query = """
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = :table_schema
          AND table_name = :table_name
        ORDER BY ordinal_position
    """

    with _engine().connect() as conn:
        result = conn.execute(text(query), {"table_schema": table_schema, "table_name": table_name})
        return [dict(row) for row in result.mappings().all()]
