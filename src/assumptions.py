"""Load the assumed inputs from config/assumptions.toml."""

import tomllib
from pathlib import Path

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "config" / "assumptions.toml"
REQUIRED_KEYS = ("value", "unit", "source", "label")


def load_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict[str, dict]:
    """Return every assumption as ``{name: {value, unit, source, label}}``.

    Raises ValueError if an item is missing a required key.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    for name, item in data.items():
        missing = [key for key in REQUIRED_KEYS if key not in item]
        if missing:
            raise ValueError(f"Assumption '{name}' is missing: {', '.join(missing)}")
    return data
