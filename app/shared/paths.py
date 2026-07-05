"""Shared project path and config helpers for Python worker code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Config paths are resolved from the repository root because scripts, tests, and
# future API subprocess calls may run from different working directories.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = PROJECT_ROOT / "app" / "shared"
CONFIG_PATH = SHARED_DIR / "config.json"
SCHEMA_PATH = SHARED_DIR / "schema.json"


def resolve_project_path(config_path: str) -> Path:
    """Resolve a config path relative to the project root.

    Absolute paths are returned unchanged. Relative paths in shared config must
    be interpreted from the project root, never from the current shell directory.
    """

    path = Path(config_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def load_config(overlay_settings: bool = False) -> dict[str, Any]:
    """Load shared runtime config.

    When *overlay_settings* is True, the ``settings`` table in the SQLite DB
    is queried and its key/value pairs override matching top-level keys in
    config.json.  This lets the Web settings page control runtime parameters
    without touching config files.
    """

    config = load_json(CONFIG_PATH)

    if overlay_settings:
        try:
            db_path = resolve_project_path(str(config.get("databasePath", "data/a_stock_research.sqlite")))
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT key, value FROM settings").fetchall()
                conn.close()
                for row in rows:
                    key = row["key"]
                    val = row["value"]
                    # Try to parse JSON values (numbers, bools, objects).
                    try:
                        parsed = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        parsed = val
                    config[key] = parsed
        except Exception:
            pass  # settings table may not exist yet

    return config


def load_schema() -> dict[str, Any]:
    """Load shared enum schema."""

    return load_json(SCHEMA_PATH)


def get_config_paths(config: dict[str, Any] | None = None) -> dict[str, Path]:
    """Return resolved filesystem paths from shared config."""

    current_config = config or load_config()
    path_keys = [
        "databasePath",
        "reportsPath",
        "logsPath",
        "rawDataPath",
        "cachePath",
    ]
    return {
        key: resolve_project_path(str(current_config[key]))
        for key in path_keys
        if key in current_config
    }


def validate_factor_weights(config: dict[str, Any] | None = None) -> None:
    """Validate that configured factor weights sum to 1."""

    current_config = config or load_config()
    factor_weights = current_config.get("factorWeights")

    if not isinstance(factor_weights, dict):
        raise ValueError("factorWeights must be an object")

    total_weight = sum(float(value) for value in factor_weights.values())
    if abs(total_weight - 1.0) > 0.000001:
        raise ValueError(f"factorWeights must sum to 1, got {total_weight}")
