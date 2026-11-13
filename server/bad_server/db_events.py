from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .bad_id import is_bad_id
from .db_backend import CompatConnection
from .db import (
    PENDING_ENROLLMENT_CAP,
    PENDING_ENROLLMENT_TTL,
    _compact_json,
    _utc_cutoff,
    logger,
    utc_now,
)

class DbEventsMixin:

    def get_device_event(self, event_id: int) -> Optional[dict[str, Any]]:
        sql = """
            SELECT e.id, e.bad_id, e.type, e.summary, e.detail_json,
                   e.created_at, d.hostname
            FROM device_events e
            LEFT JOIN devices d ON d.bad_id = e.bad_id
            WHERE e.id = %s
        """
        with self.connection() as conn:
            row = conn.execute(sql, (int(event_id),)).fetchone()
        if not row:
            return None
        return self._device_event_rows([row], include_detail=True)[0]


    def _event_list_filters(
        self,
        *,
        bad_id: Optional[str],
        q: Optional[str],
        importance: Optional[str],
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> tuple[str, list[Any]]:
        from .event_importance import types_at_least

        clauses: list[str] = []
        params: list[Any] = []
        if bad_id:
            clauses.append("e.bad_id = %s")
            params.append(bad_id)
        imp = (importance or "").strip().casefold()
        if imp and imp != "all":
            types = sorted(types_at_least(imp))
            if types:
                placeholders = ",".join("%s" for _ in types)
                clauses.append(f"e.type IN ({placeholders})")
                params.extend(types)
        elif imp != "all":
            # default UI: medium+
            types = sorted(types_at_least("medium"))
            if types:
                placeholders = ",".join("%s" for _ in types)
                clauses.append(f"e.type IN ({placeholders})")
                params.extend(types)
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            clauses.append(
                "(e.summary ILIKE %s OR e.type ILIKE %s OR d.hostname ILIKE %s "
                "OR e.bad_id ILIKE %s)"
            )
            params.extend([like, like, like, like])
        et = (event_type or "").strip()
        if et:
            clauses.append("e.type = %s")
            params.append(et)
        d_from = (date_from or "").strip()
        if d_from:
            clauses.append("e.created_at >= %s")
            params.append(f"{d_from}T00:00:00Z")
        d_to = (date_to or "").strip()
        if d_to:
            clauses.append("e.created_at <= %s")
            params.append(f"{d_to}T23:59:59Z")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params


    def list_device_events(
        self,
        *,
        bad_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        q: Optional[str] = None,
        importance: Optional[str] = None,
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_detail: bool = False,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        detail_col = ", e.detail_json" if include_detail else ""
        sql = f"""
            SELECT e.id, e.bad_id, e.type, e.summary, e.created_at,
                   d.hostname{detail_col}
            FROM device_events e
            LEFT JOIN devices d ON d.bad_id = e.bad_id
        """
        where, params = self._event_list_filters(
            bad_id=bad_id,
            q=q,
            importance=importance,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
        )
        sql += where
        sql += " ORDER BY e.created_at DESC, e.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._device_event_rows(rows, include_detail=include_detail)


    def list_unmailed_device_events(self, limit: int = 5000) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        sql = """
            SELECT e.id, e.bad_id, e.type, e.summary, e.detail_json,
                   e.created_at, d.hostname
            FROM device_events e
            LEFT JOIN devices d ON d.bad_id = e.bad_id
            WHERE e.mailed_at IS NULL
            ORDER BY e.created_at ASC, e.id ASC
            LIMIT %s
        """
        with self.connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return self._device_event_rows(rows, include_detail=True)


    def insert_device_event(
        self,
        bad_id: str,
        event_type: str,
        summary: str,
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            self._insert_device_event(
                conn,
                bad_id,
                event_type,
                summary,
                _compact_json(detail if detail is not None else {}),
                now,
            )


    def _insert_device_event(
        self,
        conn: CompatConnection,
        bad_id: str,
        event_type: str,
        summary: str,
        detail_json: str,
        created_at: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO device_events(
              bad_id, type, summary, detail_json, created_at
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (bad_id, event_type, summary, detail_json, created_at),
        )


    @staticmethod
    def _device_event_rows(
        rows: list[Any], *, include_detail: bool = False
    ) -> list[dict[str, Any]]:
        from .event_importance import event_importance

        result: list[dict[str, Any]] = []
        for row in rows:
            entry: dict[str, Any] = {
                "id": row["id"],
                "bad_id": row["bad_id"],
                "hostname": row["hostname"],
                "type": row["type"],
                "summary": row["summary"],
                "created_at": row["created_at"],
                "importance": event_importance(row["type"]),
            }
            if include_detail:
                detail: Any = None
                raw_detail = row.get("detail_json")
                if raw_detail:
                    try:
                        detail = json.loads(raw_detail)
                    except json.JSONDecodeError:
                        detail = {"_raw": raw_detail}
                entry["detail"] = detail
            result.append(entry)
        return result


    def mark_device_events_mailed(
        self, event_ids: list[int], mailed_at: str
    ) -> None:
        if not event_ids:
            return
        ids = [int(i) for i in event_ids]
        placeholders = ", ".join("%s" for _ in ids)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE device_events SET mailed_at = %s WHERE id IN ({placeholders})",
                [mailed_at, *ids],
            )


    def count_events_by_utc_day(self, days: int = 14) -> list[dict[str, Any]]:
        """События по UTC-дате: count + critical/warning (важность по типу)."""
        from datetime import timedelta

        from .event_importance import event_importance

        span = max(1, min(int(days or 14), 60))
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=span - 1)
        cutoff_dt = cutoff_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff_dt.isoformat().replace("+00:00", "Z")
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT LEFT(created_at::text, 10) AS day, type, COUNT(*)::bigint AS count
                FROM device_events
                WHERE created_at >= %s
                GROUP BY LEFT(created_at::text, 10), type
                ORDER BY day ASC
                """,
                (cutoff,),
            ).fetchall()
        by_day: dict[str, dict[str, int]] = {}
        for r in rows:
            if not r or not r["day"]:
                continue
            day = str(r["day"])
            bucket = by_day.setdefault(
                day, {"count": 0, "critical": 0, "warning": 0, "low": 0}
            )
            n = int(r["count"] or 0)
            bucket["count"] += n
            lvl = event_importance(str(r["type"] or ""))
            if lvl == "critical":
                bucket["critical"] += n
            elif lvl in {"high", "medium"}:
                bucket["warning"] += n
            elif lvl == "low":
                bucket["low"] += n
        # Заполнить пропуски нулями — иначе график «прыгает»
        out: list[dict[str, Any]] = []
        for i in range(span):
            day = (cutoff_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            b = by_day.get(day) or {
                "count": 0,
                "critical": 0,
                "warning": 0,
                "low": 0,
            }
            out.append(
                {
                    "day": day,
                    "count": int(b["count"]),
                    "critical": int(b["critical"]),
                    "warning": int(b["warning"]),
                    "low": int(b["low"]),
                }
            )
        return out


    def count_device_events(
        self,
        *,
        bad_id: Optional[str] = None,
        q: Optional[str] = None,
        importance: Optional[str] = None,
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        sql = """
            SELECT COUNT(*) AS c
            FROM device_events e
            LEFT JOIN devices d ON d.bad_id = e.bad_id
        """
        where, params = self._event_list_filters(
            bad_id=bad_id,
            q=q,
            importance=importance,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
        )
        sql += where
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["c"] if row else 0)


    def count_device_events_exact_importance(self, level: str) -> int:
        """События ровно этого уровня (не «и выше»)."""
        from .event_importance import _EVENT_IMPORTANCE, types_exact_importance

        lvl = str(level or "").strip().casefold()
        types = sorted(types_exact_importance(lvl))
        if lvl == "medium":
            known = sorted(_EVENT_IMPORTANCE.keys())
            parts: list[str] = []
            params: list[Any] = []
            if types:
                ph = ",".join("%s" for _ in types)
                parts.append(f"e.type IN ({ph})")
                params.extend(types)
            if known:
                ph = ",".join("%s" for _ in known)
                parts.append(f"e.type NOT IN ({ph})")
                params.extend(known)
            if not parts:
                return 0
            where = " OR ".join(parts)
        else:
            if not types:
                return 0
            ph = ",".join("%s" for _ in types)
            where = f"e.type IN ({ph})"
            params = list(types)
        sql = f"SELECT COUNT(*) AS c FROM device_events e WHERE {where}"
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["c"] if row else 0)
