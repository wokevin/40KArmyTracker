from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BATTLE_SIZE_OPTIONS: list[tuple[str, int]] = []

@dataclass(frozen=True)
class RosterUnitRef:
    unit_id: str
    count: int = 1
    squad_size: int | None = None

@dataclass
class RosterContext:
    roster_name: str
    points_limit: int | None
    faction_cat_path: Path
    faction_name: str
    roster_units: list[RosterUnitRef] = field(default_factory=list)
    units: list[dict] = field(default_factory=list)
    unit_index: dict[str, dict] = field(default_factory=dict)
    faction_rules: list[tuple[str, str]] = field(default_factory=list)
    warlord_unit_id: str | None = None
    leader_attachments: list[tuple[str, str]] = field(default_factory=list)