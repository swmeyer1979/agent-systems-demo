from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeResult:
    score: float
    criteria: dict[str, float]
    passed: bool


class HeuristicReportJudge:
    """Offline stand-in for an LLM judge.

    It deliberately behaves like a rubric, not like magic. Swap this boundary for
    a real model judge when API keys and review budget are available.
    """

    required_terms = {
        "durability",
        "eval",
        "trace",
        "tool",
        "cost",
        "guardrail",
        "citation",
    }

    def grade(self, report: str) -> JudgeResult:
        lower = report.lower()
        citations = set(re.findall(r"\[S[0-9]+\]", report))
        words = re.findall(r"[a-zA-Z0-9]+", report)
        criteria = {
            "citation_quality": min(1.0, len(citations) / 4),
            "coverage": len([term for term in self.required_terms if term in lower]) / len(self.required_terms),
            "specificity": 1.0 if len(words) >= 280 else len(words) / 280,
            "actionability": 1.0 if "acceptance checks" in lower and "failure modes" in lower else 0.5,
            "source_discipline": 1.0 if "sources used" in lower and "no network" in lower else 0.5,
        }
        score = round(sum(criteria.values()) / len(criteria), 3)
        return JudgeResult(score=score, criteria=criteria, passed=score >= 0.8)

