"""Profile loading from YAML files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from .models import CodeDef, Profile
from .runtime_paths import profiles_dir as _default_profiles_dir


def load_profile(profile_id: str, profiles_dir: Optional[Path] = None) -> Profile:
    """Load a profile YAML by ID. Raises FileNotFoundError if not found."""
    search_dir = Path(profiles_dir) if profiles_dir else _default_profiles_dir()
    path = search_dir / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile '{profile_id}' not found at {path}")
    return _parse_profile(path)


def load_profile_from_path(path: str | Path) -> Profile:
    return _parse_profile(Path(path))


def list_profiles(profiles_dir: Optional[Path] = None) -> list[str]:
    """Return list of available profile IDs."""
    search_dir = Path(profiles_dir) if profiles_dir else _default_profiles_dir()
    if not search_dir.exists():
        return []
    return [p.stem for p in sorted(search_dir.glob("*.yaml"))]


def _parse_profile(path: Path) -> Profile:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    codes = []
    for c in data.get("codes", []):
        codes.append(
            CodeDef(
                id=c["id"],
                label=c["label"],
                display=c.get("display", c["label"]),
                category=c.get("category", ""),
                color=c.get("color", "#EEEEEE"),
                shortcut=str(c.get("shortcut", "")),
            )
        )

    return Profile(
        id=data.get("id", path.stem),
        name=data.get("name", path.stem),
        version=str(data.get("version", "1.0")),
        reference=data.get("reference", ""),
        description=data.get("description", ""),
        codes=codes,
        analysis_padding_code=data.get("analysis_padding_code"),
        category_labels=data.get("category_labels", {}),
    )
