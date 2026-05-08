from __future__ import annotations

import re
from pathlib import Path


SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def validate_slug(value: str, field_name: str) -> str:
    if not SLUG_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must match {SLUG_RE.pattern}; got {value!r}"
        )
    return value


def safe_child_file(base_dir: Path, slug: str, suffix: str, field_name: str) -> Path:
    safe_slug = validate_slug(slug, field_name)
    base = base_dir.resolve()
    path = (base / f"{safe_slug}{suffix}").resolve(strict=False)
    if not path.is_relative_to(base):
        raise ValueError(f"{field_name} escapes base directory: {slug!r}")
    return path

