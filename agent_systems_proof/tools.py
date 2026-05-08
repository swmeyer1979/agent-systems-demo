from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .safety import safe_child_file, validate_slug


@dataclass(frozen=True)
class SourceDoc:
    source_id: str
    title: str
    path: Path
    text: str


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def register(self, name: str, fn: Callable[..., dict[str, Any]]) -> None:
        if name in self._tools:
            raise ValueError(f"duplicate tool: {name}")
        self._tools[name] = fn

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name](**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools)


def build_registry(source_dir: Path, workspace_dir: Path) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("search_sources", lambda query, limit=4: search_sources(source_dir, query, limit))
    registry.register("read_source", lambda source_id: read_source(source_dir, source_id))
    registry.register("write_report", lambda run_id, content: write_report(workspace_dir, run_id, content))
    return registry


def load_sources(source_dir: Path) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for path in sorted(source_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _extract_title(text) or path.stem.replace("_", " ").title()
        docs.append(SourceDoc(source_id=path.stem, title=title, path=path, text=text))
    return docs


def search_sources(source_dir: Path, query: str, limit: int = 4) -> dict[str, Any]:
    terms = _keywords(query)
    results = []
    for doc in load_sources(source_dir):
        doc_terms = _keywords(doc.text)
        score = len(terms & doc_terms)
        if score == 0:
            score = sum(1 for term in terms if term in doc.text.lower())
        if score:
            results.append(
                {
                    "source_id": doc.source_id,
                    "title": doc.title,
                    "score": score,
                    "preview": _best_sentence(doc.text, terms),
                }
            )
    results.sort(key=lambda item: (-item["score"], item["source_id"]))
    return {"query": query, "results": results[:limit]}


def read_source(source_dir: Path, source_id: str) -> dict[str, Any]:
    path = safe_child_file(source_dir, source_id, ".md", "source_id")
    if not path.exists():
        raise FileNotFoundError(f"source not found: {source_id}")
    text = path.read_text(encoding="utf-8")
    return {
        "source_id": source_id,
        "title": _extract_title(text) or source_id,
        "path": str(path),
        "text": text,
        "key_points": _bullet_lines(text),
    }


def write_report(workspace_dir: Path, run_id: str, content: str) -> dict[str, Any]:
    validate_slug(run_id, "run_id")
    report_dir = workspace_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = safe_child_file(report_dir, run_id, ".md", "run_id")
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def _keywords(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "you",
        "your",
        "are",
        "agent",
        "agents",
        "system",
        "systems",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 3 and token not in stop
    }


def _best_sentence(text: str, terms: set[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    ranked = sorted(
        sentences,
        key=lambda sentence: sum(1 for term in terms if term in sentence.lower()),
        reverse=True,
    )
    return ranked[0][:220].strip() if ranked else ""


def _bullet_lines(text: str) -> list[str]:
    points = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            points.append(stripped.removeprefix("- ").strip())
    return points[:8]
