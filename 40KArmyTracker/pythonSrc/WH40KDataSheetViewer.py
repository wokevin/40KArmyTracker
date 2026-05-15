import re
import textwrap
from pathlib import Path
from xml.etree import ElementTree as ET

import WH40KModels
from WH40KModels import BATTLE_SIZE_OPTIONS, RosterContext, RosterUnitRef
from WH40KDataSheetParser import (
    CATEGORY_PRIORITY, MELEE_COLS, RANGED_COLS, UNIT_STATS, UNIT_TYPES,
    MenuEntry, get_factions, group_factions_by_army, load_gst_data, parse_units,
)
from WH40KRosterHandler import (
    _battle_size_label, _default_roster_meta, _ensure_ctx_meta, _meta_tag_suffix,
    _parse_unit_line, _save_roster_context,
    build_unit_index, render_roster_snapshot, save_roster_snapshot, validate_roster,
)

ROSTERS_DIR = Path(__file__).parent.parent / "rosters"
WRAP_WIDTH = 100
DISPLAY_WIDTH = 110


def hr(ch: str = "─", width: int = DISPLAY_WIDTH) -> str:
    return ch * width

def wrap_lines(text: str, indent: str = "    ") -> list[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=WRAP_WIDTH, initial_indent=indent, subsequent_indent=indent)

def print_weapon_table(
    weapons: list[tuple[str, dict[str, str]]],
    cols: list[str],
    header: str,
    base_indent: str = "",
) -> None:
    if not weapons:
        return

    name_width = max(len("Name"), max(len(w[0]) for w in weapons))
    col_widths = [max(len(col), max(len(w[1].get(col, "—")) for w in weapons)) for col in cols]
    separator = "  "
    line_width = name_width + len(separator) + sum(col_widths) + len(separator) * (len(cols) - 1)

    print(f"\n{base_indent}  {header}")
    print(f"{base_indent}  " + "─" * line_width)
    print(
        f"{base_indent}  "
        + f"{'Name':<{name_width}}"
        + separator
        + separator.join(f"{col:^{width}}" for col, width in zip(cols, col_widths))
    )
    print(f"{base_indent}  " + "─" * line_width)

    for weapon_name, chars in weapons:
        print(
            f"{base_indent}  "
            + f"{weapon_name:<{name_width}}"
            + separator
            + separator.join(f"{chars.get(col, '—'):^{width}}" for col, width in zip(cols, col_widths))
        )

def print_rules_block(title: str, rules: list[tuple[str, str]], base_indent: str = "") -> None:
    if not rules:
        return
    print(f"\n{base_indent}  {title}")
    print(f"{base_indent}  " + hr("─", DISPLAY_WIDTH - 2))
    for name, desc in rules:
        print(f"\n{base_indent}  {name}")
        for line in wrap_lines(desc, indent=f"{base_indent}    "):
            print(line)

def display_unit(unit: dict, faction_rules: list[tuple[str, str]] | None = None) -> None:
    print()
    print(hr("═"))

    pts_label = f"  ·  {unit['pts']} pts" if unit["pts"] is not None else ""
    mn, mx = unit.get("unit_min"), unit.get("unit_max")
    if mn is not None and mx is not None:
        size_label = f"  ·  {mn}-{mx} models"
    elif mx is not None:
        size_label = f"  ·  max {mx} models"
    elif mn is not None:
        size_label = f"  ·  min {mn} models"
    else:
        size_label = ""

    print(f"  {unit['name'].upper()}{pts_label}{size_label}")
    print(hr("─"))

    if unit["type_keywords"]:
        kw_line = "  TYPE:      " + "  ·  ".join(kw.upper() for kw in unit["type_keywords"])
        for line in textwrap.wrap(kw_line, width=DISPLAY_WIDTH, subsequent_indent="             "):
            print(line)

    if unit["special_keywords"]:
        special_line = "  SPECIAL:   " + "  ·  ".join(kw.upper() for kw in unit["special_keywords"])
        for line in textwrap.wrap(special_line, width=DISPLAY_WIDTH, subsequent_indent="             "):
            print(line)

    if unit["faction_keywords"]:
        faction_line = "  FACTION:   " + "  ·  ".join(kw.upper() for kw in unit["faction_keywords"])
        for line in textwrap.wrap(faction_line, width=DISPLAY_WIDTH, subsequent_indent="             "):
            print(line)


    print_rules_block("UNIT RULES", unit["rules"])

    if unit["unit_abilities"]:
        print_rules_block("UNIT-LEVEL ABILITIES", unit["unit_abilities"])

    for index, model in enumerate(unit["models"]):
        model_indent = "\t\t" if index > 0 else ""

        if len(unit["models"]) > 1:
            count_note = f" (x{model['count']})" if model["count"] > 1 else ""
            title = f"{model['name'].upper()}{count_note}"
            print(f"\n{model_indent}  {title}")
            print(f"{model_indent}  " + "─" * min(DISPLAY_WIDTH - 2, len(title) + 8))

        stats = model["stats"]
        present_stats = [stat for stat in UNIT_STATS if stat in stats]
        if present_stats:
            cell_width = 9
            print()
            print(f"{model_indent}  " + "".join(f"{stat:^{cell_width}}" for stat in present_stats))
            print(f"{model_indent}  " + "".join(f"{stats[stat]:^{cell_width}}" for stat in present_stats))
        else:
            print(f"\n{model_indent}  [No Unit stat block found for this model]")

        if model.get("transport_cap") is not None:
            print(f"{model_indent}  TRANSPORT CAPACITY: {model['transport_cap']}")

        if model["rules"]:
            print_rules_block("MODEL RULES", model["rules"], base_indent=model_indent)

        print_weapon_table(model["ranged"], RANGED_COLS, "RANGED WEAPONS", base_indent=model_indent)
        print_weapon_table(model["melee"], MELEE_COLS, "MELEE WEAPONS", base_indent=model_indent)

        if model["abilities"]:
            print_rules_block("ABILITIES", model["abilities"], base_indent=model_indent)

    print()
    print(hr("═"))

def get_unit_type(unit: dict) -> str:
    keywords = set(unit.get("type_keywords", []) + unit.get("special_keywords", []))
    if "Character" in keywords or "Epic Hero" in keywords:
        return "Character"
    for unit_type in UNIT_TYPES:
        if unit_type in keywords:
            return unit_type
    return "Other"

def _is_epic_hero(unit: dict) -> bool:
    type_keywords = set(unit.get("type_keywords", []) or [])
    special_keywords = set(unit.get("special_keywords", []) or [])
    return "Epic Hero" in type_keywords or "Epic Hero" in special_keywords

def _existing_unit_picks(active_roster: list[RosterUnitRef], unit_id: str) -> int:
    total = 0
    for ref in active_roster:
        if ref.unit_id == unit_id:
            total += max(1, int(ref.count))
    return total

def group_units(units: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: list[tuple[str, list[dict]]] = []
    for group_name in CATEGORY_PRIORITY + ["Other"]:
        grouped = [unit for unit in units if get_unit_type(unit) == group_name]
        if grouped:
            groups.append((group_name, grouped))
    return groups

def ask_choice(
    prompt: str,
    min_n: int,
    max_n: int,
    allow_back: bool = False,
    allow_home: bool = False,
) -> str:
    while True:
        raw = input(prompt).strip().upper()
        if allow_back and raw == "B":
            return "B"
        if allow_home and raw == "H":
            return "H"
        if raw.isdigit() and min_n <= int(raw) <= max_n:
            return raw

        message = f"Please enter a number between {min_n} and {max_n}"
        if allow_back:
            message += ", B"
        if allow_home:
            message += ", H"
        print("  " + message + ".")

def _ask_int_in_range(prompt: str, min_value: int, max_value: int) -> int:
    value: int | None = None
    while value is None or value < min_value or value > max_value:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  Invalid input. Enter a whole number in range {min_value}-{max_value}.")
            continue

        if value < min_value or value > max_value:
            print(f"  Out of range. Enter a value between {min_value} and {max_value}.")

    return value

def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    while True:
        raw = input(prompt).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("  Invalid input. Enter Y or N.")

def _pick_single_wargear(unit: dict) -> tuple[str, ...]:
    _ = unit
    return ()

def _pick_model_variant_split(unit: dict, squad_size: int) -> tuple[str, ...]:
    variants = unit.get("model_variants", []) or []
    if not variants or len(variants) < 2 or squad_size < 1:
        return ()

    print("\n  Model composition:")
    print(f"  Total models: {squad_size}")

    remaining = squad_size
    picks: list[tuple[str, int]] = []

    for i, variant in enumerate(variants):
        variant_name = str(variant.get("name", f"Variant {i+1}"))

        if i == len(variants) - 1:
            count = remaining
            picks.append((variant_name, count))
            print(f"  {variant_name}: {count} (remaining)")
            break

        max_allowed = remaining
        variant_max = variant.get("max")
        if isinstance(variant_max, int) and variant_max >= 0:
            max_allowed = min(max_allowed, variant_max)

        count = _ask_int_in_range(f"  {variant_name} [0-{max_allowed}]: ", 0, max_allowed)
        picks.append((variant_name, count))
        remaining -= count

    if sum(count for _, count in picks) != squad_size:
        return ()

    return tuple(f"{name}={count}" for name, count in picks if count > 0)

def _variant_summary(variant_split: tuple[str, ...]) -> str:
    if not variant_split:
        return ""
    return ", ".join(variant_split)

def _refresh_roster_context(ctx: RosterContext, gst_rules: dict) -> None:
    ctx.units, ctx.faction_rules = parse_units(ctx.faction_cat_path, gst_rules)
    ctx.unit_index = build_unit_index(ctx.units)
    roster_ids = {ref.unit_id for ref in ctx.roster_units}
    if ctx.warlord_unit_id and ctx.warlord_unit_id not in roster_ids:
        ctx.warlord_unit_id = None
    deduped: list[tuple[str, str]] = []
    seen_leaders: set[str] = set()
    for leader_id, squad_id in ctx.leader_attachments:
        if leader_id not in roster_ids or squad_id not in roster_ids:
            continue
        if leader_id in seen_leaders:
            continue
        seen_leaders.add(leader_id)
        deduped.append((leader_id, squad_id))
    ctx.leader_attachments = deduped

def _find_faction_cat_path(faction_name: str) -> Path | None:
    for cat_path, full_name, _short_name, _army_group, _sub_prefix in get_factions():
        if full_name == faction_name:
            return cat_path
    return None

def _resolve_unit_id_by_name(by_name: dict[str, list[str]], unit_name: str) -> str | None:
    key = unit_name.strip().lower()
    if not key:
        return None
    ids = by_name.get(key, [])
    return ids[0] if ids else None

def _roster_rows(ctx: RosterContext) -> list[tuple[int, RosterUnitRef, dict]]:
    rows: list[tuple[int, RosterUnitRef, dict]] = []
    for index, ref in enumerate(ctx.roster_units, 1):
        unit = ctx.unit_index.get(ref.unit_id)
        if unit is not None:
            rows.append((index, ref, unit))
    return rows

def _roster_rows_with_units(active_roster: list[RosterUnitRef], units: list[dict]) -> list[tuple[int, RosterUnitRef, dict]]:
    unit_map = {u["id"]: u for u in units if u.get("id")}
    rows: list[tuple[int, RosterUnitRef, dict]] = []
    for index, ref in enumerate(active_roster, 1):
        if ref.unit_id in unit_map:
            rows.append((index, ref, unit_map[ref.unit_id]))
    return rows

def _attachment_label(ctx: RosterContext, leader_id: str, squad_id: str) -> str:
    leader = ctx.unit_index.get(leader_id)
    squad = ctx.unit_index.get(squad_id)
    leader_name = leader["name"] if leader else leader_id
    squad_name = squad["name"] if squad else squad_id
    return f"{leader_name} -> {squad_name}"

def _print_command_state(ctx: RosterContext) -> None:
    if ctx.warlord_unit_id:
        warlord = ctx.unit_index.get(ctx.warlord_unit_id)
        warlord_name = warlord["name"] if warlord else ctx.warlord_unit_id
        print(f"  Warlord: {warlord_name}")
    else:
        print("  Warlord: (none)")
    if not ctx.leader_attachments:
        print("  Leaders: (none)")
        return
    print("  Leaders:")
    for leader_id, squad_id in ctx.leader_attachments:
        print(f"    - {_attachment_label(ctx, leader_id, squad_id)}")

def _edit_warlord(ctx: RosterContext) -> None:
    candidates = [(idx, ref, unit) for idx, ref, unit in _roster_rows(ctx) if get_unit_type(unit) == "Character"]
    if not candidates:
        print("  No Character or Epic Hero units in roster.")
        return
    print("\n  SET WARLORD\n")
    for idx, ref, unit in candidates:
        marker = " [CURRENT]" if ref.unit_id == ctx.warlord_unit_id else ""
        print(f"  {idx}. {unit['name']}{marker}")
    print("  0. Clear warlord")
    print("  B. Back\n")
    choice_map = {str(idx): ref.unit_id for idx, ref, _unit in candidates}
    while True:
        raw = input("Choice: ").strip().upper()
        if raw == "B":
            return
        if raw == "0":
            ctx.warlord_unit_id = None
            print("  Warlord cleared.")
            return
        if raw in choice_map:
            ctx.warlord_unit_id = choice_map[raw]
            warlord = ctx.unit_index.get(ctx.warlord_unit_id)
            print(f"  Warlord set: {warlord['name'] if warlord else ctx.warlord_unit_id}")
            return
        print("  Please enter a listed number, 0, or B.")

def _add_or_update_leader_attachment(ctx: RosterContext) -> None:
    leader_rows = [(idx, ref, unit) for idx, ref, unit in _roster_rows(ctx) if unit.get("leader_targets")]
    if not leader_rows:
        print("  No leader-capable units in roster.")
        return
    print("\n  SELECT LEADER\n")
    for idx, _ref, unit in leader_rows:
        print(f"  {idx}. {unit['name']}")
    print("  B. Back\n")
    leader_map = {str(idx): (ref, unit) for idx, ref, unit in leader_rows}
    chosen_ref: RosterUnitRef | None = None
    chosen_unit: dict | None = None
    while True:
        raw = input("Leader: ").strip().upper()
        if raw == "B":
            return
        if raw in leader_map:
            chosen_ref, chosen_unit = leader_map[raw]
            break
        print("  Please enter a listed number or B.")
    assert chosen_ref is not None and chosen_unit is not None
    valid_targets = {name.lower() for name in chosen_unit.get("leader_targets", [])}
    squad_rows = [
        (idx, ref, unit)
        for idx, ref, unit in _roster_rows(ctx)
        if ref.unit_id != chosen_ref.unit_id and unit["name"].lower() in valid_targets
    ]
    if not squad_rows:
        print(f"  No valid target squads in roster for {chosen_unit['name']}.")
        return
    print(f"\n  VALID TARGETS FOR {chosen_unit['name'].upper()}\n")
    for idx, _ref, unit in squad_rows:
        print(f"  {idx}. {unit['name']}")
    print("  B. Back\n")
    squad_map = {str(idx): ref.unit_id for idx, ref, _unit in squad_rows}
    while True:
        raw = input("Target squad: ").strip().upper()
        if raw == "B":
            return
        if raw in squad_map:
            target_squad_id = squad_map[raw]
            ctx.leader_attachments = [
                (leader_id, squad_id)
                for leader_id, squad_id in ctx.leader_attachments
                if leader_id != chosen_ref.unit_id
            ]
            ctx.leader_attachments.append((chosen_ref.unit_id, target_squad_id))
            print(f"  Attached {chosen_unit['name']} to {ctx.unit_index[target_squad_id]['name']}.")
            return
        print("  Please enter a listed number or B.")

def _remove_leader_attachment(ctx: RosterContext) -> None:
    if not ctx.leader_attachments:
        print("  No leader attachments to remove.")
        return
    print("\n  CURRENT ATTACHMENTS\n")
    for idx, (leader_id, squad_id) in enumerate(ctx.leader_attachments, 1):
        print(f"  {idx}. {_attachment_label(ctx, leader_id, squad_id)}")
    print("  B. Back\n")
    while True:
        raw = input("Remove which: ").strip().upper()
        if raw == "B":
            return
        if raw.isdigit() and 1 <= int(raw) <= len(ctx.leader_attachments):
            removed = ctx.leader_attachments.pop(int(raw) - 1)
            print(f"  Removed {_attachment_label(ctx, removed[0], removed[1])}.")
            return
        print(f"  Please enter 1-{len(ctx.leader_attachments)} or B.")

def _edit_leaders(ctx: RosterContext) -> None:
    while True:
        print("\n  LEADER ATTACHMENTS")
        print(hr("─"))
        if ctx.leader_attachments:
            for leader_id, squad_id in ctx.leader_attachments:
                print(f"  - {_attachment_label(ctx, leader_id, squad_id)}")
        else:
            print("  (none)")
        print("\n  A. Add or Update  |  R. Remove  |  B. Back\n")
        raw = input("Choice: ").strip().upper()
        if raw == "B":
            return
        if raw == "A":
            _add_or_update_leader_attachment(ctx)
        elif raw == "R":
            _remove_leader_attachment(ctx)
        else:
            print("  Please enter A, R, or B.")

def _load_roster_from_txt(txt_path: Path, gst_rules: dict) -> RosterContext | None:
    try:
        raw_lines = txt_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None

    roster_name = ""
    faction_name = ""
    points_limit: int | None = None
    parsed_units: list[tuple[str, int, int | None, dict[str, object]]] = []
    parsed_warlord_name: str | None = None
    parsed_attachments: list[tuple[str, str]] = []

    for raw in raw_lines:
        line = raw.strip()
        if line.startswith("ROSTER: "):
            roster_name = line[len("ROSTER: "):].strip()
        elif line.startswith("FACTION: "):
            faction_name = line[len("FACTION: "):].strip()
        elif line.startswith("POINTS LIMIT: "):
            pts_raw = line[len("POINTS LIMIT: "):].strip()
            points_limit = int(pts_raw) if pts_raw.isdigit() and int(pts_raw) > 0 else None
        elif line.startswith("UNIT: "):
            parsed_units.append(_parse_unit_line(line[len("UNIT: "):]))
        elif line.startswith("WARLORD: "):
            parsed_warlord_name = line[len("WARLORD: "):].strip() or None
        elif line.startswith("LEADER: "):
            payload = line[len("LEADER: "):].strip()
            if "->" in payload:
                leader_name, squad_name = payload.split("->", 1)
                leader_name = leader_name.strip()
                squad_name = squad_name.strip()
                if leader_name and squad_name:
                    parsed_attachments.append((leader_name, squad_name))

    if not roster_name or not faction_name:
        return None

    faction_cat_path = _find_faction_cat_path(faction_name)
    if faction_cat_path is None:
        return None

    ctx = RosterContext(roster_name, points_limit, faction_cat_path, faction_name)
    setattr(ctx, "roster_unit_meta", [])

    _refresh_roster_context(ctx, gst_rules)

    by_name: dict[str, list[str]] = {}
    for unit in ctx.units:
        unit_id = unit.get("id")
        unit_name = str(unit.get("name", "")).strip().lower()
        if unit_id and unit_name:
            by_name.setdefault(unit_name, []).append(unit_id)

    meta = _ensure_ctx_meta(ctx)
    for unit_name, count, squad_size, unit_meta in parsed_units:
        unit_id = _resolve_unit_id_by_name(by_name, unit_name)
        if not unit_id:
            continue
        ctx.roster_units.append(RosterUnitRef(unit_id=unit_id, count=count, squad_size=squad_size))
        meta.append(unit_meta)

    _ensure_ctx_meta(ctx)
    if parsed_warlord_name:
        warlord_id = _resolve_unit_id_by_name(by_name, parsed_warlord_name)
        if warlord_id and any(ref.unit_id == warlord_id for ref in ctx.roster_units):
            ctx.warlord_unit_id = warlord_id
    for leader_name, squad_name in parsed_attachments:
        leader_id = _resolve_unit_id_by_name(by_name, leader_name)
        squad_id = _resolve_unit_id_by_name(by_name, squad_name)
        if not leader_id or not squad_id:
            continue
        if any(ref.unit_id == leader_id for ref in ctx.roster_units) and any(ref.unit_id == squad_id for ref in ctx.roster_units):
            ctx.leader_attachments.append((leader_id, squad_id))
    _refresh_roster_context(ctx, gst_rules)
    return ctx

def browse_faction(
    cat_file: Path,
    full_name: str,
    gst_rules: dict,
    active_roster: list[RosterUnitRef] | None = None,
    active_roster_meta: list[dict[str, object]] | None = None,
    active_leader_attachments: list[tuple[str, str]] | None = None,
) -> str:
    print(f"\nParsing {full_name}...\n")
    units, faction_rules = parse_units(cat_file, gst_rules)

    if not units:
        print("No units found in this catalogue.")
        return "back"

    if active_roster is not None and active_roster_meta is not None:
        while len(active_roster_meta) < len(active_roster):
            active_roster_meta.append(_default_roster_meta())

    print(hr("═"))
    print(f"  {full_name}  —  {len(units)} units")
    print(hr("═"))

    input("\n  Press Enter to browse categories...")
    unit_groups = group_units(units)

    while True:
        print("\n" + hr("─"))
        print("  CATEGORIES")
        print(hr("─"))
        for index, (category_name, category_units) in enumerate(unit_groups, 1):
            print(f"  {index}. {category_name} ({len(category_units)})")
        print("  B. Back")
        print("  H. Home")
        print("  0. Quit\n")

        category_choice = ask_choice(f"Select category [1-{len(unit_groups)}], B back, H home, or 0 quit: ", 0, len(unit_groups), allow_back=True, allow_home=True)

        if category_choice == "0":
            print("\nGoodbye.\n")
            return "quit"
        if category_choice == "H":
            return "home"
        if category_choice == "B":
            return "back"

        category_name, category_units = unit_groups[int(category_choice) - 1]

        while True:
            print("\n" + hr("─"))
            print(f"  {category_name.upper()} UNITS")
            print(hr("─"))

            for index, unit in enumerate(category_units, 1):
                pts = f" ({unit['pts']} pts)" if unit["pts"] is not None else ""
                mn, mx = unit.get("unit_min"), unit.get("unit_max")
                if mn is not None and mx is not None:
                    size = f" [{mn}-{mx}]"
                elif mx is not None:
                    size = f" [max {mx}]"
                elif mn is not None:
                    size = f" [min {mn}]"
                else:
                    size = ""
                model_note = f" ({len(unit['models'])} model types)" if len(unit["models"]) > 1 else ""
                print(f"  {index}. {unit['name']}{pts}{size}{model_note}")
            print("  B. Back")
            print("  H. Home")
            print("  0. Quit\n")

            unit_choice = ask_choice(f"Select unit [1-{len(category_units)}], B back, H home, or 0 quit: ", 0, len(category_units), allow_back=True, allow_home=True)

            if unit_choice == "0":
                print("\nGoodbye.\n")
                return "quit"
            if unit_choice == "H":
                return "home"
            if unit_choice == "B":
                break

            display_unit(category_units[int(unit_choice) - 1], faction_rules)

            if active_roster is not None:
                action = input("  Press Enter to return, or A to add to roster: ").strip().upper()
                if action == "A":
                    unit = category_units[int(unit_choice) - 1]
                    unit_id = unit.get("id")
                    if not unit_id:
                        print("  Cannot add this unit (missing unit id).")
                        continue

                    existing_picks = _existing_unit_picks(active_roster, unit_id)
                    if _is_epic_hero(unit) and existing_picks >= 1:
                        print(f"  Cannot add {unit['name']}: Epic Hero units are unique (max 1).")
                        continue

                    unit_min = unit.get("unit_min")
                    unit_max = unit.get("unit_max")
                    is_squadable = (isinstance(unit_min, int) and unit_min > 1) or (isinstance(unit_max, int) and unit_max > 1)

                    if is_squadable:
                        min_allowed = unit_min if isinstance(unit_min, int) and unit_min > 0 else 1
                        max_allowed = unit_max if isinstance(unit_max, int) and unit_max >= min_allowed else min_allowed
                        squad_size = _ask_int_in_range(
                            f"  Squad size [{min_allowed}-{max_allowed}]: ",
                            min_allowed,
                            max_allowed,
                        )
                        variant_split = _pick_model_variant_split(unit, squad_size)
                        active_roster.append(RosterUnitRef(unit_id=unit_id, count=1, squad_size=squad_size))

                        if active_roster_meta is not None:
                            active_roster_meta.append({
                                "wargear": (),
                                "variant_split": variant_split,
                            })

                        suffix = f" [VAR:{_variant_summary(variant_split)}]" if variant_split else ""
                        print(f"  Added {unit['name']} (squad of {squad_size}){suffix} to roster.")
                    else:
                        variant_split = _pick_model_variant_split(unit, 1)
                        active_roster.append(RosterUnitRef(unit_id=unit_id, count=1))

                        if active_roster_meta is not None:
                            active_roster_meta.append({
                                "wargear": (),
                                "variant_split": variant_split,
                            })

                        suffix = f" [VAR:{_variant_summary(variant_split)}]" if variant_split else ""
                        print(f"  Added {unit['name']} x1{suffix} to roster.")

                    if unit.get("leader_targets") and active_roster and active_leader_attachments is not None:
                        valid_target_names = {name.lower() for name in unit.get("leader_targets", [])}
                        squad_candidates = [
                            (idx, ref, u)
                            for idx, ref, u in _roster_rows_with_units(active_roster, units)
                            if u["name"].lower() in valid_target_names and ref.unit_id != unit_id
                        ]
                        if squad_candidates and _ask_yes_no("  Attach to squad now? [Y/N]: ", default=False):
                            print("\n  Valid targets:\n")
                            for idx, _ref, u in squad_candidates:
                                print(f"  {idx}. {u['name']}")
                            print()
                            choice = ask_choice(f"Attach to [1-{len(squad_candidates)}] or 0 skip: ", 0, len(squad_candidates))
                            if choice != "0":
                                target_ref = squad_candidates[int(choice) - 1][1]
                                active_leader_attachments.append((unit_id, target_ref.unit_id))
                                target_unit = next((u for _idx, ref, u in squad_candidates if ref.unit_id == target_ref.unit_id), None)
                                target_name = target_unit["name"] if target_unit else target_ref.unit_id
                                print(f"  Attached {unit['name']} to {target_name}.")
            else:
                input("  Press Enter to return to this category...")

def _pick_faction(faction_groups: list[tuple[str, list[MenuEntry]]], prompt_verb: str = "ROSTER") -> tuple[Path, str] | None:
    while True:
        print(f"\nSELECT FACTION - {prompt_verb}\n")
        for index, (group_name, group_factions) in enumerate(faction_groups, 1):
            print(f"  {index}. {group_name} ({len(group_factions)})")
        print("  0. Cancel\n")

        group_choice = ask_choice(f"Select army group [1-{len(faction_groups)}] or 0 cancel: ", 0, len(faction_groups))
        if group_choice == "0":
            return None

        army_group_name, menu_entries = faction_groups[int(group_choice) - 1]

        while True:
            print(f"\nFACTIONS - {army_group_name}\n")
            for index, (entry_type, entry_data) in enumerate(menu_entries, 1):
                if entry_type == "subgroup":
                    subgroup_name, sub_factions = entry_data
                    print(f"  {index}. {subgroup_name}  ({len(sub_factions)} factions)")
                else:
                    print(f"  {index}. {entry_data[2]}")
            print("  B. Back")
            print("  0. Cancel\n")

            faction_choice = ask_choice(f"Select [1-{len(menu_entries)}], B back, or 0 cancel: ", 0, len(menu_entries), allow_back=True)
            if faction_choice == "0":
                return None
            if faction_choice == "B":
                break

            entry_type, entry_data = menu_entries[int(faction_choice) - 1]

            if entry_type == "subgroup":
                subgroup_name, sub_factions = entry_data
                while True:
                    print(f"\n{subgroup_name.upper()} FACTIONS\n")
                    for sub_index, sub_faction in enumerate(sub_factions, 1):
                        print(f"  {sub_index}. {sub_faction[2]}")
                    print("  B. Back")
                    print("  0. Quit\n")

                    sub_choice = ask_choice(f"Select faction [1-{len(sub_factions)}], B back, or 0 quit: ", 0, len(sub_factions), allow_back=True)
                    if sub_choice == "B":
                        break
                    if sub_choice == "0":
                        print("\nGoodbye.\n")
                        return
                    chosen = sub_factions[int(sub_choice) - 1]
                    return chosen[0], chosen[1]
            else:
                return entry_data[0], entry_data[1]

def _list_saved_rosters() -> list[Path]:
    if not ROSTERS_DIR.exists():
        return []
    return sorted(ROSTERS_DIR.glob("*.txt"))

def _pick_saved_roster(verb: str = "Select") -> Path | None:
    saved = _list_saved_rosters()
    if not saved:
        print("  No saved rosters found.")
        return None

    print(f"\n  {verb.upper()} A ROSTER\n")
    for index, path in enumerate(saved, 1):
        print(f"  {index}. {path.stem}")
    print("  0. Cancel\n")

    choice = ask_choice(f"Select roster [1-{len(saved)}] or 0 cancel: ", 0, len(saved))
    if choice == "0":
        return None
    return saved[int(choice) - 1]

def _pick_points_limit() -> int | None:
    print("\n  SELECT BATTLE SIZE\n")
    for index, (name, pts) in enumerate(BATTLE_SIZE_OPTIONS, 1):
        print(f"  {index}. {name} ({pts} pts)")
    print(f"  {len(BATTLE_SIZE_OPTIONS) + 1}. Custom points")
    print("  0. No limit\n")

    choice = ask_choice(
        f"Select [1-{len(BATTLE_SIZE_OPTIONS) + 1}] or 0 for no limit: ",
        0,
        len(BATTLE_SIZE_OPTIONS) + 1,
    )
    if choice == "0":
        return None
    idx = int(choice) - 1
    if idx < len(BATTLE_SIZE_OPTIONS):
        return BATTLE_SIZE_OPTIONS[idx][1]
    while True:
        raw = input("  Enter custom points limit: ").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("  Please enter a positive integer.")

def _new_roster(faction_groups: list[tuple[str, list[MenuEntry]]], gst_rules: dict) -> str:
    name_raw = input("\n  Roster name: ").strip()
    if not name_raw:
        print("  Cancelled.")
        return "back"

    points_limit = _pick_points_limit()

    result = _pick_faction(faction_groups, "NEW ROSTER")
    if result is None:
        return "back"

    chosen_cat, chosen_name = result
    ctx = RosterContext(name_raw, points_limit, chosen_cat, chosen_name)
    setattr(ctx, "roster_unit_meta", [])

    action = browse_faction(
        ctx.faction_cat_path,
        ctx.faction_name,
        gst_rules,
        ctx.roster_units,
        _ensure_ctx_meta(ctx),
        ctx.leader_attachments,
    )
    if action == "quit":
        return "quit"

    if not ctx.roster_units:
        print("\n  No units added. Roster not saved.")
        return "back"

    _refresh_roster_context(ctx, gst_rules)
    while True:
        print("\n  COMMAND ASSIGNMENTS")
        print(hr("─"))
        _print_command_state(ctx)
        print("\n  W. Warlord  |  L. Leaders  |  D. Done\n")
        raw = input("Choice: ").strip().upper()
        if raw == "D":
            break
        if raw == "W":
            _edit_warlord(ctx)
        elif raw == "L":
            _edit_leaders(ctx)
        else:
            print("  Please enter W, L, or D.")
    issues, total_pts = validate_roster(ctx.roster_units, ctx.unit_index, ctx.points_limit, ctx.warlord_unit_id, ctx.leader_attachments)

    print()
    if issues:
        print("  VALIDATION ISSUES:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  Validation: PASSED")

    pts_display = f"{total_pts} / {ctx.points_limit} pts" if ctx.points_limit is not None else f"{total_pts} pts"
    print(f"  Total: {pts_display}")
    print(f"  Battle size: {_battle_size_label(total_pts)}")

    save_raw = input("\n  Save roster? [Y/N]: ").strip().upper()
    if save_raw != "Y":
        print("  Roster not saved.")
        return "back"

    slug = "".join(char if char.isalnum() or char in " _-" else "_" for char in ctx.roster_name).strip().replace(" ", "_")
    txt_path = ROSTERS_DIR / f"{slug}.txt"
    _save_roster_context(ctx, txt_path)
    print(f"  Saved: {txt_path.name}")
    return "back"

def _view_roster(gst_rules: dict) -> None:
    txt_path = _pick_saved_roster("View")
    if txt_path is None:
        return

    ctx = _load_roster_from_txt(txt_path, gst_rules)
    if ctx is None:
        print("  Could not load roster file.")
        return

    snapshot = render_roster_snapshot(
        ctx.roster_name,
        ctx.faction_name,
        ctx.roster_units,
        ctx.unit_index,
        ctx.faction_rules,
        ctx.points_limit,
        ctx.warlord_unit_id,
        ctx.leader_attachments,
    )
    print()
    print(snapshot)

def _edit_roster(gst_rules: dict) -> str:
    txt_path = _pick_saved_roster("Edit")
    if txt_path is None:
        return "back"

    ctx = _load_roster_from_txt(txt_path, gst_rules)
    if ctx is None:
        print("  Could not load roster file.")
        return "back"

    while True:
        print(f"\n  EDITING: {ctx.roster_name}  ({ctx.faction_name})")
        print(hr("─"))
        _print_command_state(ctx)

        meta = _ensure_ctx_meta(ctx)

        if not ctx.roster_units:
            print("  (empty)")
        for index, ref in enumerate(ctx.roster_units, 1):
            unit = ctx.unit_index.get(ref.unit_id)
            unit_name = unit["name"] if unit else ref.unit_id

            unit_meta = meta[index - 1]
            markers: list[str] = []
            wg = tuple(unit_meta.get("wargear", ()) or ())
            if wg:
                markers.append(f"WG:{wg[0]}")
            variant_split = tuple(unit_meta.get("variant_split", ()) or ())
            if variant_split:
                markers.append("VAR:" + ", ".join(variant_split))
            if ref.unit_id == ctx.warlord_unit_id:
                markers.append("WARLORD")
            for leader_id, squad_id in ctx.leader_attachments:
                if leader_id == ref.unit_id:
                    squad = ctx.unit_index.get(squad_id)
                    markers.append(f"LEADS:{squad['name'] if squad else squad_id}")
            suffix = f" [{' | '.join(markers)}]" if markers else ""

            print(f"  {index}. {unit_name} x{ref.count}{suffix}")

        print("\n  A. Add units (browse)  |  R. Remove unit  |  W. Warlord  |  L. Leaders  |  D. Done  |  0. Discard\n")
        raw = input("Choice: ").strip().upper()

        if raw == "0":
            print("  Changes discarded.")
            return "back"

        if raw == "D":
            break

        if raw == "A":
            action = browse_faction(
                ctx.faction_cat_path,
                ctx.faction_name,
                gst_rules,
                ctx.roster_units,
                _ensure_ctx_meta(ctx),
                ctx.leader_attachments,
            )
            if action == "quit":
                return "quit"

        elif raw == "R":
            if not ctx.roster_units:
                print("  Nothing to remove.")
                continue
            remove_raw = input(f"  Remove unit number [1-{len(ctx.roster_units)}]: ").strip()
            if remove_raw.isdigit() and 1 <= int(remove_raw) <= len(ctx.roster_units):
                remove_idx = int(remove_raw) - 1
                removed = ctx.roster_units.pop(remove_idx)
                meta = _ensure_ctx_meta(ctx)
                if remove_idx < len(meta):
                    meta.pop(remove_idx)
                _refresh_roster_context(ctx, gst_rules)
                unit = ctx.unit_index.get(removed.unit_id)
                unit_name = unit["name"] if unit else removed.unit_id
                print(f"  Removed {unit_name}.")
            else:
                print(f"  Please enter 1-{len(ctx.roster_units)}.")
        elif raw == "W":
            _edit_warlord(ctx)
        elif raw == "L":
            _edit_leaders(ctx)

    if not ctx.roster_units:
        print("  Roster is empty. Not saved.")
        return "back"

    _refresh_roster_context(ctx, gst_rules)
    issues, total_pts = validate_roster(ctx.roster_units, ctx.unit_index, ctx.points_limit, ctx.warlord_unit_id, ctx.leader_attachments)

    print()
    if issues:
        print("  VALIDATION ISSUES:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  Validation: PASSED")

    pts_display = f"{total_pts} / {ctx.points_limit} pts" if ctx.points_limit is not None else f"{total_pts} pts"
    print(f"  Total: {pts_display}")
    print(f"  Battle size: {_battle_size_label(total_pts)}")

    save_raw = input("\n  Save changes? [Y/N]: ").strip().upper()
    if save_raw != "Y":
        print("  Changes discarded.")
        return "back"

    _save_roster_context(ctx, txt_path)
    print(f"  Saved: {txt_path.name}")
    return "back"

def _delete_roster() -> None:
    txt_path = _pick_saved_roster("Delete")
    if txt_path is None:
        return

    confirm = input(f"  Delete '{txt_path.stem}'? [Y/N]: ").strip().upper()
    if confirm != "Y":
        print("  Cancelled.")
        return

    txt_path.unlink(missing_ok=True)
    print(f"  Deleted {txt_path.stem}.")

def _roster_manager(faction_groups: list[tuple[str, list[MenuEntry]]], gst_rules: dict) -> str:
    while True:
        print("\n" + hr("═"))
        print("  ROSTER MANAGER")
        print(hr("═"))
        print("  1. New Roster")
        print("  2. View Roster")
        print("  3. Edit Roster")
        print("  4. Delete Roster")
        print("  B. Back")
        print("  0. Quit\n")

        raw = input("Choice [1-4], B, or 0: ").strip().upper()
        if raw == "B":
            return "back"
        if raw == "0":
            print("\nGoodbye.\n")
            return "quit"

        if raw == "1":
            action = _new_roster(faction_groups, gst_rules)
            if action == "quit":
                return "quit"
        elif raw == "2":
            _view_roster(gst_rules)
        elif raw == "3":
            action = _edit_roster(gst_rules)
            if action == "quit":
                return "quit"
        elif raw == "4":
            _delete_roster()

def main() -> None:
    factions = get_factions()
    if not factions:
        print("No .cat files found in data.")
        return

    gst_rules, battle_sizes = load_gst_data()
    WH40KModels.BATTLE_SIZE_OPTIONS[:] = battle_sizes
    faction_groups = group_factions_by_army(factions)

    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                 Warhammer 40K Datasheet Viewer                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    while True:
        print("\nROOT MENU - ARMY GROUPS\n")
        for index, (group_name, group_factions) in enumerate(faction_groups, 1):
            print(f"  {index}. {group_name} ({len(group_factions)})")
        print("  R. Roster Manager")
        print("  0. Quit\n")

        group_choice: str | None = None
        while group_choice is None:
            raw = input(f"Select army group [1-{len(faction_groups)}], R roster manager, or 0 to quit: ").strip().upper()

            if raw == "0":
                print("\nGoodbye.\n")
                return

            if raw == "R":
                action = _roster_manager(faction_groups, gst_rules)
                if action == "quit":
                    return
                break

            if raw.isdigit() and 1 <= int(raw) <= len(faction_groups):
                group_choice = raw
            else:
                print(f"  Please enter 1-{len(faction_groups)}, R, or 0.")

        if group_choice is None:
            continue

        army_group_name, menu_entries = faction_groups[int(group_choice) - 1]

        while True:
            print(f"\nFACTIONS - {army_group_name}\n")
            for index, (entry_type, entry_data) in enumerate(menu_entries, 1):
                if entry_type == "subgroup":
                    subgroup_name, sub_factions = entry_data
                    print(f"  {index}. {subgroup_name}  ({len(sub_factions)} factions)")
                else:
                    print(f"  {index}. {entry_data[2]}")
            print("  B. Back")
            print("  0. Quit\n")

            faction_choice = ask_choice(f"Select [1-{len(menu_entries)}], B back, or 0 quit: ", 0, len(menu_entries), allow_back=True)

            if faction_choice == "0":
                print("\nGoodbye.\n")
                return
            if faction_choice == "B":
                break

            entry_type, entry_data = menu_entries[int(faction_choice) - 1]

            if entry_type == "subgroup":
                subgroup_name, sub_factions = entry_data
                while True:
                    print(f"\n{subgroup_name.upper()} FACTIONS\n")
                    for sub_index, sub_faction in enumerate(sub_factions, 1):
                        print(f"  {sub_index}. {sub_faction[2]}")
                    print("  B. Back")
                    print("  0. Quit\n")

                    sub_choice = ask_choice(f"Select faction [1-{len(sub_factions)}], B back, or 0 quit: ", 0, len(sub_factions), allow_back=True)
                    if sub_choice == "B":
                        break
                    if sub_choice == "0":
                        print("\nGoodbye.\n")
                        return
                    chosen = sub_factions[int(sub_choice) - 1]
                    result = browse_faction(chosen[0], chosen[1], gst_rules)
                    if result == "quit":
                        return
            else:
                result = browse_faction(entry_data[0], entry_data[1], gst_rules)
                if result == "quit":
                    return

if __name__ == "__main__":
    main()