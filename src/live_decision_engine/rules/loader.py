from functools import lru_cache
from pathlib import Path

import yaml

_RULES_DIR = Path(__file__).parent


def _load_yaml(name: str) -> dict:
    with (_RULES_DIR / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def load_patterns() -> list[dict]:
    return _load_yaml("patterns.yaml")["patterns"]


@lru_cache(maxsize=None)
def load_rules() -> tuple[list[dict], dict, dict]:
    data = _load_yaml("decisions.yaml")
    return data["rules"], data["fallback"], data["stage_map"]


@lru_cache(maxsize=None)
def load_actions() -> dict[str, dict]:
    return _load_yaml("actions.yaml")["actions"]


@lru_cache(maxsize=None)
def load_action_stages() -> dict[str, list[str]]:
    return _load_yaml("decisions.yaml")["action_stages"]
