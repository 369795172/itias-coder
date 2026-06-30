"""Data models for ITIAS Coder."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CodeDef:
    """A single code definition from a profile."""
    id: int
    label: str
    display: str
    category: str
    color: str
    shortcut: str = ""


@dataclass
class Profile:
    """An encoding profile (e.g. ITIAS, IFIAS)."""
    id: str
    name: str
    version: str
    reference: str
    description: str
    codes: list[CodeDef]
    analysis_padding_code: Optional[int] = None
    category_labels: dict[str, str] = field(default_factory=dict)

    def get_code(self, code_id: int) -> Optional[CodeDef]:
        for c in self.codes:
            if c.id == code_id:
                return c
        return None

    def shortcut_map(self) -> dict[str, int]:
        return {c.shortcut: c.id for c in self.codes if c.shortcut}


@dataclass
class Segment:
    """One sliced video segment with optional code."""
    index: int          # 1-based display index
    filepath: str
    code_id: Optional[int] = None
    code_label: Optional[str] = None
    coded_at: Optional[str] = None  # ISO timestamp string

    @property
    def filename(self) -> str:
        return os.path.basename(self.filepath)

    @property
    def is_coded(self) -> bool:
        return self.code_id is not None

    def apply_code(self, code: CodeDef) -> None:
        self.code_id = code.id
        self.code_label = code.label
        self.coded_at = datetime.now().isoformat()

    def clear_code(self) -> None:
        self.code_id = None
        self.code_label = None
        self.coded_at = None

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "filepath": self.filepath,
            "code_id": self.code_id,
            "code_label": self.code_label,
            "coded_at": self.coded_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(
            index=d["index"],
            filepath=d["filepath"],
            code_id=d.get("code_id"),
            code_label=d.get("code_label"),
            coded_at=d.get("coded_at"),
        )


@dataclass
class Session:
    """Encoding session state."""
    segments: list[Segment]
    profile_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    segments_folder: str = ""

    @property
    def total(self) -> int:
        return len(self.segments)

    @property
    def coded_count(self) -> int:
        return sum(1 for s in self.segments if s.is_coded)

    @property
    def is_complete(self) -> bool:
        return self.coded_count == self.total

    def first_uncoded_index(self) -> Optional[int]:
        """Return 0-based index of first uncoded segment, or None."""
        for i, s in enumerate(self.segments):
            if not s.is_coded:
                return i
        return None

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "segments_folder": self.segments_folder,
            "created_at": self.created_at,
            "segments": [s.to_dict() for s in self.segments],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        segments = [Segment.from_dict(s) for s in d.get("segments", [])]
        return cls(
            segments=segments,
            profile_id=d.get("profile_id", "itias_default"),
            created_at=d.get("created_at", datetime.now().isoformat()),
            segments_folder=d.get("segments_folder", ""),
        )
