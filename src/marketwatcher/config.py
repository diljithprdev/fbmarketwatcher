from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import AppConfig


def load_config(path: str | Path) -> AppConfig:
    """Load, parse, and validate config.yaml. Exits on fatal errors."""
    config_path = Path(path)
    if not config_path.exists():
        print(f"ERROR Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"ERROR Failed to parse config YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw, dict):
        print("ERROR Config file is empty or not a YAML mapping.", file=sys.stderr)
        sys.exit(1)

    try:
        config = AppConfig.model_validate(raw)
    except ValidationError as exc:
        print(f"ERROR Invalid config:\n{exc}", file=sys.stderr)
        sys.exit(1)

    if not config.watches:
        print("WARNING No watches defined in config.", file=sys.stderr)

    return config
