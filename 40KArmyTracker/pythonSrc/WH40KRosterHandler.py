from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from WH40KModels import BATTLE_SIZE_OPTIONS, RosterContext, RosterUnitRef
from WH40KDataSheetParser import MELEE_COLS, RANGED_COLS, UNIT_STATS


@dataclass(frozen=True)
class RosterUnitRef:
    unit_id: str
    count: int = 1
    squad_size: int | None = None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _unit_points(unit: dict[str, Any]) -> int | None:
    pts = unit.get("pts")
    if pts is None:
        return None
    return _safe_int(pts, 0)


def _resolved_squad_size(unit: dict[str, Any], ref: RosterUnitRef) -> int:
    if ref.squad_size is not None and ref.squad_size > 0:
        return ref.squad_size

    unit_min = unit.get("unit_min")
    if isinstance(unit_min, int) and unit_min > 0:
        return unit_min

    return 1


def validate_roster(roster_units: list[RosterUnitRef], unit_index: dict[str, dict[str, Any]], points_limit: int | None = None, warlord_unit_id: str | None = None, leader_attachments: list[tuple[str, str]] | None = None) -> tuple[list[str], int]:
    issues: list[str] = []
    total_points = 0

    for ref in roster_units:
        if ref.count < 1:
            issues.append(f"{ref.unit_id}: count must be at least 1.")
            continue

        unit = unit_index.get(ref.unit_id)
        if unit is None:
            issues.append(f"{ref.unit_id}: unit id could not be resolved.")
            continue

        squad_size = _resolved_squad_size(unit, ref)
        unit_min = unit.get("unit_min")
        unit_max = unit.get("unit_max")

        if isinstance(unit_min, int) and squad_size < unit_min:
            issues.append(f"{unit['name']}: squad size {squad_size} is below minimum {unit_min}.)")

        if isinstance(unit_max, int) and squad_size > unit_max:
            issues.append(f"{unit['name']}: squad size {squad_size} exceeds maximum {unit_max}.)")

        pts = _unit_points(unit)
        if pts is not None:
            unit_min_for_pts = unit.get("unit_min")
            if isinstance(unit_min_for_pts, int) and unit_min_for_pts > 1:
                per_model = pts // unit_min_for_pts
                total_points += per_model * squad_size * ref.count
            else:
                total_points += pts * ref.count

    if points_limit is not None and total_points > points_limit:
        issues.append(f"Army total {total_points} exceeds points cap {points_limit}.)")

    if warlord_unit_id is not None:
        if not any(ref.unit_id == warlord_unit_id for ref in roster_units):
            wu = unit_index.get(warlord_unit_id)
            issues.append(f"Warlord '{wu['name'] if wu else warlord_unit_id}' is not in the roster.")

    for leader_id, squad_id in (leader_attachments or []):
        leader_unit = unit_index.get(leader_id)
        squad_unit = unit_index.get(squad_id)
        if not leader_unit or not squad_unit:
            continue
        if not any(ref.unit_id == squad_id for ref in roster_units):
            issues.append(f"'{leader_unit['name']}' is attached to '{squad_unit['name']}' which is not in the roster.")
        valid_lower = {t.lower() for t in leader_unit.get("leader_targets", [])}
        if valid_lower and squad_unit["name"].lower() not in valid_lower:
            issues.append(f"'{leader_unit['name']}' cannot lead '{squad_unit['name']}' (not a valid target).")

    return issues, total_points


def _weapon_line(name: str, chars: dict[str, str], cols: list[str]) -> str:
    parts = [f"{col}:{chars.get(col, '—')}" for col in cols]
    return f"      - {name} | " + " | ".join(parts)


def _render_named_rules(title: str, rules: list[tuple[str, str]]) -> list[str]:
    lines: list[str] = []
    if not rules:
        return lines

    lines.append(title)
    for rule_name, rule_desc in rules:
        lines.append(f"  - {rule_name}")
        if rule_desc:
            for part in str(rule_desc).splitlines():
                if part.strip():
                    lines.append(f"    {part.strip()}")
    lines.append("")
    return lines


def _render_model_block(model: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    model_name = model.get("name", "Unknown Model")
    model_count = _safe_int(model.get("count", 1), 1)

    count_suffix = f" x{model_count}" if model_count > 1 else ""
    lines.append(f"    MODEL: {model_name}{count_suffix}")

    stats = model.get("stats", {}) or {}
    stat_parts = []
    for stat in UNIT_STATS:
        if stat in stats:
            stat_parts.append(f"{stat}:{stats[stat]}")
    if stat_parts:
        lines.append("      Stats: " + " | ".join(stat_parts))

    ranged = model.get("ranged", []) or []
    if ranged:
        lines.append("      Ranged Weapons:")
        for weapon_name, chars in ranged:
            lines.append(_weapon_line(weapon_name, chars or {}, RANGED_COLS))

    melee = model.get("melee", []) or []
    if melee:
        lines.append("      Melee Weapons:")
        for weapon_name, chars in melee:
            lines.append(_weapon_line(weapon_name, chars or {}, MELEE_COLS))

    typed_weapons = model.get("typed_weapons", []) or []
    if typed_weapons:
        section_order: list[str] = []
        section_map: dict[str, list[tuple[str, dict[str, str]]]] = {}
        for section_name, weapon_name, chars in typed_weapons:
            if section_name not in section_map:
                section_map[section_name] = []
                section_order.append(section_name)
            section_map[section_name].append((weapon_name, chars or {}))

        for section_name in section_order:
            lines.append(f"      {section_name}:")
            for weapon_name, chars in section_map[section_name]:
                char_keys = set(chars.keys())
                cols = RANGED_COLS if "BS" in char_keys or "Range" in char_keys else MELEE_COLS
                lines.append(_weapon_line(weapon_name, chars, cols))

    transport_cap = model.get("transport_cap")
    if transport_cap:
        lines.append(f"      Transport Capacity: {transport_cap}")

    rules = model.get("rules", []) or []
    if rules:
        lines.append("      Rules:")
        for rule_name, rule_desc in rules:
            lines.append(f"        - {rule_name}")
            if rule_desc:
                for part in str(rule_desc).splitlines():
                    if part.strip():
                        lines.append(f"          {part.strip()}")

    abilities = model.get("abilities", []) or []
    if abilities:
        lines.append("      Abilities:")
        for ability_name, ability_desc in abilities:
            lines.append(f"        - {ability_name}")
            if ability_desc:
                for part in str(ability_desc).splitlines():
                    if part.strip():
                        lines.append(f"          {part.strip()}")

    return lines


def _is_character(unit: dict[str, Any]) -> bool:
    types = set(unit.get("type_keywords", []) or [])
    specials = set(unit.get("special_keywords", []) or [])
    return "Character" in types or "Epic Hero" in specials


def _is_vehicle(unit: dict[str, Any]) -> bool:
    types = set(unit.get("type_keywords", []) or [])
    return "Vehicle" in types or "Walker" in types or "Monster" in types


def _is_infantry(unit: dict[str, Any]) -> bool:
    types = set(unit.get("type_keywords", []) or [])
    return "Infantry" in types


def _is_squad(unit: dict[str, Any]) -> bool:
    specials = set(unit.get("special_keywords", []) or [])
    if "Battleline" in specials:
        return True

    unit_min = unit.get("unit_min")
    unit_max = unit.get("unit_max")
    if isinstance(unit_min, int) and unit_min > 1:
        return True
    if isinstance(unit_max, int) and unit_max > 1:
        return True

    models = unit.get("models", []) or []
    return len(models) > 1


def _bucket_name(unit: dict[str, Any]) -> str:
    if _is_character(unit):
        return "Characters"
    if _is_vehicle(unit):
        return "Vehicles"
    if _is_squad(unit):
        return "Squads"
    if _is_infantry(unit):
        return "Infantry"
    return "Other"


def _render_unit(unit: dict[str, Any], ref: RosterUnitRef, faction_rules: list[tuple[str, str]] | None = None, is_warlord: bool = False, leading_squad: str | None = None) -> tuple[list[str], int]:
    lines: list[str] = []

    unit_name = unit.get("name", "Unknown Unit")
    roster_count = max(1, _safe_int(ref.count, 1))
    squad_size = _resolved_squad_size(unit, ref)

    unit_pts = _unit_points(unit)
    unit_min = unit.get("unit_min")

    badges: list[str] = []
    if is_warlord:
        badges.append("★ WARLORD")
    if leading_squad:
        badges.append(f"LEADING: {leading_squad}")
    badge_str = f"  [{', '.join(badges)}]" if badges else ""

    if isinstance(unit_min, int) and unit_min > 1:
        unit_label = f"{unit_name} ({squad_size} models)"
        if roster_count > 1:
            unit_label += f" x{roster_count}"
        lines.append(f"  UNIT: {unit_label}{badge_str}")

        per_model = (unit_pts // unit_min) if unit_pts is not None else None
        total_pts = (per_model or 0) * squad_size * roster_count
        if per_model is not None:
            lines.append(f"    Cost: {per_model} pts per model | {total_pts} pts total")
        else:
            lines.append("    Cost: Unknown")
    else:
        unit_label = unit_name
        if roster_count > 1:
            unit_label += f" x{roster_count}"
        lines.append(f"  UNIT: {unit_label}{badge_str}")

        total_pts = (unit_pts or 0) * roster_count
        if unit_pts is not None:
            lines.append(f"    Cost: {unit_pts} pts" + (f" | {total_pts} pts total" if roster_count > 1 else ""))
        else:
            lines.append("    Cost: Unknown")

    models = unit.get("models", []) or []
    if models:
        lines.append("    Models:")
        for model in models:
            lines.extend(_render_model_block(model))

    type_keywords = unit.get("type_keywords", []) or []
    special_keywords = unit.get("special_keywords", []) or []
    faction_keywords = unit.get("faction_keywords", []) or []

    if type_keywords:
        lines.append("    Type Keywords: " + ", ".join(type_keywords))
    if special_keywords:
        lines.append("    Special Keywords: " + ", ".join(special_keywords))
    if faction_keywords:
        lines.append("    Faction Keywords: " + ", ".join(faction_keywords))

    if faction_rules:
        lines.extend(_render_named_rules("    Faction / Detachment Rules:", faction_rules))

    rules = unit.get("rules", []) or []
    if rules:
        lines.append("    Unit Rules:")
        faction_rule_names = {name.strip().lower() for name, _ in (faction_rules or [])}
        rules = [(name, desc) for name, desc in (unit.get("rules", []) or []) if name.strip().lower() not in faction_rule_names]
        for rule_name, rule_desc in rules:
            lines.append(f"      - {rule_name}")
            if rule_desc:
                for part in str(rule_desc).splitlines():
                    if part.strip():
                        lines.append(f"        {part.strip()}")

    unit_abilities = unit.get("unit_abilities", []) or []
    if unit_abilities:
        lines.append("    Unit Abilities:")
        for ability_name, ability_desc in unit_abilities:
            lines.append(f"      - {ability_name}")
            if ability_desc:
                for part in str(ability_desc).splitlines():
                    if part.strip():
                        lines.append(f"        {part.strip()}")

    lines.append("")
    return lines, total_pts


def build_unit_index(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for unit in units:
        uid = unit.get("id")
        if uid:
            index[str(uid)] = unit
    return index


def render_roster_snapshot(roster_name: str, faction_name: str, roster_units: list[RosterUnitRef], unit_index: dict[str, dict[str, Any]], faction_rules: list[tuple[str, str]] | None = None, points_limit: int | None = None, warlord_unit_id: str | None = None, leader_attachments: list[tuple[str, str]] | None = None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    roster_faction_rules = faction_rules or []
    roster_leader_attachments = leader_attachments or []

    issues, grand_total = validate_roster(roster_units, unit_index, points_limit, warlord_unit_id, leader_attachments)

    leader_map: dict[str, str] = {}
    for ldr_id, sq_id in leader_attachments:
        sq = unit_index.get(sq_id)
        if sq:
            leader_map[ldr_id] = sq["name"]

    buckets: dict[str, list[tuple[dict[str, Any], RosterUnitRef]]] = {"Squads": [], "Infantry": [], "Vehicles": [], "Characters": [], "Other": []}

    unresolved: list[RosterUnitRef] = []
    for ref in roster_units:
        unit = unit_index.get(ref.unit_id)
        if not unit:
            unresolved.append(ref)
            continue
        buckets[_bucket_name(unit)].append((unit, ref))

    lines: list[str] = []
    lines.append("=" * 110)
    lines.append(f"ROSTER: {roster_name}")
    lines.append(f"FACTION: {faction_name}")
    if points_limit is not None:
        lines.append(f"POINTS LIMIT: {points_limit}")
    lines.append(f"GENERATED: {now}")
    lines.append("=" * 110)
    lines.append("")

    lines.append("VALIDATION")
    if issues:
        lines.append("  Status: FAILED")
        for issue in issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("  Status: PASSED")
    lines.append("")

    lines.append("ARMY COMPOSITION")
    lines.append("-" * 110)

    composition: dict[str, int] = {}
    for ref in roster_units:
        unit = unit_index.get(ref.unit_id)
        unit_name = unit["name"] if unit else f"[UNRESOLVED] {ref.unit_id}"
        composition[unit_name] = composition.get(unit_name, 0) + max(1, _safe_int(ref.count, 1))

    for unit_name in sorted(composition):
        lines.append(f"  - {unit_name}: x{composition[unit_name]}")

    lines.append("")

    for section in ["Squads", "Infantry", "Vehicles", "Characters", "Other"]:
        section_rows = buckets.get(section, [])
        if not section_rows:
            continue

        lines.append(section.upper())
        lines.append("-" * 110)

        section_total = 0
        section_units = 0
        section_entries = 0

        for unit, ref in section_rows:
            unit_id = str(unit.get("id", ""))
            unit_lines, unit_pts_total = _render_unit(unit, ref, faction_rules, is_warlord=(unit_id == warlord_unit_id), leading_squad=leader_map.get(unit_id))
            lines.extend(unit_lines)
            section_total += unit_pts_total
            section_units += max(1, _safe_int(ref.count, 1))
            section_entries += 1

        lines.append(f"  [{section}] entries={section_entries} | total unit picks={section_units} | total points={section_total}")
        lines.append("")

    if unresolved:
        lines.append("UNRESOLVED UNIT IDS")
        lines.append("-" * 110)
        for ref in unresolved:
            lines.append(f"  - {ref.unit_id} | count={ref.count} | squad_size={ref.squad_size}")
        lines.append("")

    lines.append("=" * 110)
    if points_limit is None:
        lines.append(f"ROSTER TOTAL: {grand_total} pts")
    else:
        lines.append(f"ROSTER TOTAL: {grand_total} / {points_limit} pts")
    lines.append("=" * 110)

    return "\n".join(lines)

def save_roster_snapshot(file_path: str, roster_snapshot: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(roster_snapshot)

def _battle_size_label(total_pts: int) -> str:
    label = "Unknown"
    for name, cap in BATTLE_SIZE_OPTIONS:
        if total_pts <= cap:
            return name
        label = name
    return label

def _default_roster_meta() -> dict[str, object]:
    return {"wargear": [], "variant_split": []}

def _meta_tag_suffix(unit_meta: dict[str, object]) -> str:
    markers: list[str] = []
    wg = tuple(unit_meta.get("wargear", ()) or ())
    if wg:
        markers.append(f"WG:{wg[0]}")
    variant_split = tuple(unit_meta.get("variant_split", ()) or ())
    if variant_split:
        markers.append("VAR:" + ", ".join(variant_split))
    return f" [{' | '.join(markers)}]" if markers else ""

def _ensure_ctx_meta(ctx: RosterContext) -> list[dict[str, object]]:
    if not hasattr(ctx, "roster_unit_meta"):
        setattr(ctx, "roster_unit_meta", [])
    meta: list[dict[str, object]] = ctx.roster_unit_meta
    while len(meta) < len(ctx.roster_units):
        meta.append(_default_roster_meta())
    while len(meta) > len(ctx.roster_units):
        meta.pop()
    return meta

def _parse_unit_line(text: str) -> tuple[str, int, int | None, dict[str, object]]:
    badge_match = re.search(r'\s+\[.*?\]$', text)
    if badge_match:
        text = text[:badge_match.start()]
    text = text.strip()
    count = 1
    squad_size: int | None = None
    count_match = re.search(r'\s+x(\d+)$', text)
    if count_match:
        count = int(count_match.group(1))
        text = text[:count_match.start()].strip()
    models_match = re.search(r'\s+\((\d+)\s+models?\)$', text)
    if models_match:
        squad_size = int(models_match.group(1))
        text = text[:models_match.start()].strip()
    return text, count, squad_size, _default_roster_meta()

def _save_roster_context(ctx: RosterContext, txt_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"ROSTER: {ctx.roster_name}")
    lines.append(f"FACTION: {ctx.faction_name}")
    if ctx.points_limit is not None:
        lines.append(f"POINTS LIMIT: {ctx.points_limit}")
    for ref in ctx.roster_units:
        unit = ctx.unit_index.get(ref.unit_id)
        unit_name = unit["name"] if unit else ref.unit_id
        unit_min = unit.get("unit_min") if unit else None
        if isinstance(unit_min, int) and unit_min > 1:
            squad_size = ref.squad_size or unit_min
            label = f"{unit_name} ({squad_size} models)"
        else:
            label = unit_name
        if ref.count > 1:
            label += f" x{ref.count}"
        lines.append(f"UNIT: {label}")
    if ctx.warlord_unit_id:
        wu = ctx.unit_index.get(ctx.warlord_unit_id)
        lines.append(f"WARLORD: {wu['name'] if wu else ctx.warlord_unit_id}")
    for ldr_id, sq_id in ctx.leader_attachments:
        lu = ctx.unit_index.get(ldr_id)
        su = ctx.unit_index.get(sq_id)
        if lu and su:
            lines.append(f"LEADER: {lu['name']} -> {su['name']}")
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
