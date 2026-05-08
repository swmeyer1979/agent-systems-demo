from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    question: str
    status: str
    current_step: int
    total_steps: int
    output_path: str | None


class RunStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists runs (
                    run_id text primary key,
                    question text not null,
                    status text not null,
                    current_step integer not null,
                    total_steps integer not null,
                    output_path text,
                    created_at real not null,
                    updated_at real not null
                );

                create table if not exists steps (
                    run_id text not null,
                    step_index integer not null,
                    name text not null,
                    status text not null,
                    input_json text not null,
                    output_json text,
                    error text,
                    started_at real not null,
                    finished_at real,
                    primary key (run_id, step_index),
                    foreign key (run_id) references runs(run_id)
                );

                create table if not exists tool_calls (
                    id integer primary key autoincrement,
                    run_id text not null,
                    step_index integer not null,
                    tool_name text not null,
                    args_json text not null,
                    output_json text,
                    status text not null,
                    latency_ms real not null,
                    created_at real not null
                );
                """
            )

    def create_run(self, run_id: str, question: str, total_steps: int, overwrite: bool) -> None:
        now = time.time()
        with self.connect() as conn:
            if overwrite:
                conn.execute("delete from tool_calls where run_id = ?", (run_id,))
                conn.execute("delete from steps where run_id = ?", (run_id,))
                conn.execute("delete from runs where run_id = ?", (run_id,))
            conn.execute(
                """
                insert into runs (run_id, question, status, current_step, total_steps, created_at, updated_at)
                values (?, ?, 'running', 0, ?, ?, ?)
                """,
                (run_id, question, total_steps, now, now),
            )

    def get_run(self, run_id: str) -> RunRecord | None:
        with self.connect() as conn:
            row = conn.execute("select * from runs where run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return RunRecord(
            run_id=row["run_id"],
            question=row["question"],
            status=row["status"],
            current_step=row["current_step"],
            total_steps=row["total_steps"],
            output_path=row["output_path"],
        )

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        current_step: int | None = None,
        output_path: str | None = None,
    ) -> None:
        existing = self.get_run(run_id)
        if existing is None:
            raise KeyError(f"unknown run_id: {run_id}")
        next_status = status if status is not None else existing.status
        next_step = current_step if current_step is not None else existing.current_step
        next_output = output_path if output_path is not None else existing.output_path
        with self.connect() as conn:
            conn.execute(
                """
                update runs
                set status = ?, current_step = ?, output_path = ?, updated_at = ?
                where run_id = ?
                """,
                (next_status, next_step, next_output, time.time(), run_id),
            )

    def start_step(self, run_id: str, step_index: int, name: str, input_payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert or replace into steps
                    (run_id, step_index, name, status, input_json, output_json, error, started_at, finished_at)
                values (?, ?, ?, 'running', ?, null, null, ?, null)
                """,
                (run_id, step_index, name, json.dumps(input_payload, sort_keys=True), time.time()),
            )

    def finish_step(
        self,
        run_id: str,
        step_index: int,
        output_payload: dict[str, Any],
        *,
        status: str = "done",
        error: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                update steps
                set status = ?, output_json = ?, error = ?, finished_at = ?
                where run_id = ? and step_index = ?
                """,
                (status, json.dumps(output_payload, sort_keys=True), error, time.time(), run_id, step_index),
            )

    def get_step_output(self, run_id: str, name: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                select output_json from steps
                where run_id = ? and name = ? and status = 'done'
                order by step_index desc limit 1
                """,
                (run_id, name),
            ).fetchone()
        if row is None or row["output_json"] is None:
            return None
        return json.loads(row["output_json"])

    def completed_steps(self, run_id: str) -> dict[int, dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "select step_index, output_json from steps where run_id = ? and status = 'done'",
                (run_id,),
            ).fetchall()
        return {row["step_index"]: json.loads(row["output_json"]) for row in rows}

    def list_step_names(self, run_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "select name from steps where run_id = ? and status = 'done' order by step_index",
                (run_id,),
            ).fetchall()
        return [row["name"] for row in rows]

    def record_tool_call(
        self,
        run_id: str,
        step_index: int,
        tool_name: str,
        args: dict[str, Any],
        output: dict[str, Any],
        *,
        status: str,
        latency_ms: float,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into tool_calls
                    (run_id, step_index, tool_name, args_json, output_json, status, latency_ms, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step_index,
                    tool_name,
                    json.dumps(args, sort_keys=True),
                    json.dumps(output, sort_keys=True),
                    status,
                    latency_ms,
                    time.time(),
                ),
            )

    def list_tool_names(self, run_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "select tool_name from tool_calls where run_id = ? and status = 'ok' order by id",
                (run_id,),
            ).fetchall()
        return [row["tool_name"] for row in rows]

    def list_tool_calls(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                select step_index, tool_name, args_json, output_json, status, latency_ms
                from tool_calls
                where run_id = ?
                order by id
                """,
                (run_id,),
            ).fetchall()
        return [
            {
                "step_index": row["step_index"],
                "tool_name": row["tool_name"],
                "args": json.loads(row["args_json"]),
                "output": json.loads(row["output_json"]) if row["output_json"] else None,
                "status": row["status"],
                "latency_ms": row["latency_ms"],
            }
            for row in rows
        ]
