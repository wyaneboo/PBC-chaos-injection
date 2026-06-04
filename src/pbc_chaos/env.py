"""Environment file loading helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> bool:
    """Load key-value pairs from a local env file without overriding real env vars."""

    env_path = Path(path)
    if not env_path.is_absolute():
        env_path = Path.cwd() / env_path
    if not env_path.exists():
        return False

    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)
    return True


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    return key, _clean_env_value(value)


def _clean_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned
