from __future__ import annotations

import json


def parse_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def json_dumps(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=True)


def json_loads(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


def normalize_skills(skills: list[str]) -> list[str]:
    return sorted({skill.strip().lower() for skill in skills if skill.strip()})
