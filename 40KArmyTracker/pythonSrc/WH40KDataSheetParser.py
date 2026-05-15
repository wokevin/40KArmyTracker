from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS_CAT = "http://www.battlescribe.net/schema/catalogueSchema"
NS_GST = "http://www.battlescribe.net/schema/gameSystemSchema"

DATA_DIR = Path(__file__).parent.parent / "data"
GST_FILE = DATA_DIR / "Warhammer 40,000.gst"

UNIT_STATS: list[str] = []
RANGED_COLS: list[str] = []
MELEE_COLS: list[str] = []
UNIT_TYPES: list[str] = []

CATEGORY_PRIORITY = [
    "Character", "Epic Hero", "Infantry", "Mounted", "Beast", "Monster", "Vehicle", "Walker",
    "Aircraft", "Transport", "Dedicated Transport", "Fortification", "Titanic",
]

FACTION_PREFIX = "Faction: "

ARMY_GROUP_ORDER = ["Imperium", "Chaos", "Xenos", "Other"]

ARMY_GROUP_REMAP: dict[str, str] = {
    "Imperium": "Imperium",
    "Chaos": "Chaos",
    "Xenos": "Xenos",
    "Unaligned Forces": "Other",
}

STRUCTURAL_CATEGORY_NAMES = {"Configuration", "Unit"}
STAT_PROFILE_TYPES: set[str] = set()
PROFILE_TYPE_COLS: dict[str, list[str]] = {}
GST_CATEGORY_INDEX: dict[str, str] = {}
ACTIVE_CATEGORY_INDEX: dict[str, str] = {}

MenuEntry = tuple[str, object]

_MARKUP_RE = re.compile(r"[\^*]+")
_LEADER_HEADER_RE = re.compile(
    r"This (?:model|unit) can be attached to the following units?:\s*",
    re.IGNORECASE,
)
_BATTLE_SIZE_PT_RE = re.compile(r"\((\d+)\s+Point", re.IGNORECASE)

def _parse_profile_type_columns(root: ET.Element, namespace: str) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    profile_types = root.find(f"{{{namespace}}}profileTypes")
    if profile_types is None:
        return output

    for profile_type in profile_types.findall(f"{{{namespace}}}profileType"):
        profile_name = (profile_type.get("name") or "").strip()
        if not profile_name:
            continue

        cols: list[str] = []
        characteristic_types = profile_type.find(f"{{{namespace}}}characteristicTypes")
        if characteristic_types is not None:
            for characteristic_type in characteristic_types.findall(f"{{{namespace}}}characteristicType"):
                characteristic_name = (characteristic_type.get("name") or "").strip()
                if characteristic_name:
                    cols.append(characteristic_name)

        output[profile_name] = cols

    return output

def _build_category_index(roots: list[ET.Element], namespace: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for root in roots:
        category_entries = root.find(f"{{{namespace}}}categoryEntries")
        if category_entries is None:
            continue

        for category_entry in category_entries.findall(f"{{{namespace}}}categoryEntry"):
            category_id = category_entry.get("id")
            category_name = (category_entry.get("name") or "").strip()
            if category_id and category_name and category_id not in output:
                output[category_id] = category_name

    return output

def _resolve_category_name(category_link: ET.Element) -> str:
    target_id = category_link.get("targetId")
    if target_id and target_id in ACTIVE_CATEGORY_INDEX:
        return ACTIVE_CATEGORY_INDEX[target_id]
    return (category_link.get("name") or "").strip()

def _refresh_gst_source_metadata(root: ET.Element) -> None:
    profile_type_cols = _parse_profile_type_columns(root, NS_GST)

    PROFILE_TYPE_COLS.clear()
    PROFILE_TYPE_COLS.update(profile_type_cols)

    UNIT_STATS[:] = profile_type_cols.get("Unit", [])
    RANGED_COLS[:] = profile_type_cols.get("Ranged Weapons", [])
    MELEE_COLS[:] = profile_type_cols.get("Melee Weapons", [])

    STAT_PROFILE_TYPES.clear()
    for profile_name in ("Unit", "Ranged Weapons", "Melee Weapons", "Transport"):
        if profile_name in profile_type_cols:
            STAT_PROFILE_TYPES.add(profile_name)

    GST_CATEGORY_INDEX.clear()
    GST_CATEGORY_INDEX.update(_build_category_index([root], NS_GST))

    available_categories = set(GST_CATEGORY_INDEX.values())
    UNIT_TYPES[:] = [name for name in CATEGORY_PRIORITY if name in available_categories]

def xml_chars(profile: ET.Element, namespace: str) -> dict[str, str]:
    return {
        c.get("name", ""): _MARKUP_RE.sub("", c.text or "—").strip() or "—"
        for c in profile.findall(f".//{{{namespace}}}characteristic")
    }

def dedupe_named_text(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    output: list[tuple[str, str]] = []
    for name, text in items:
        key = (" ".join((name or "").split()), " ".join((text or "").split()))
        if key in seen:
            continue
        seen.add(key)
        output.append((name, text))
    return output

def parse_rules_index(root: ET.Element, namespace: str) -> dict[str, tuple[str, str]]:
    output: dict[str, tuple[str, str]] = {}
    shared_rules = root.find(f"{{{namespace}}}sharedRules")
    if shared_rules is None:
        return output
    for rule in shared_rules.findall(f"{{{namespace}}}rule"):
        rule_id = rule.get("id")
        if not rule_id:
            continue
        name = rule.get("name", "Unnamed Rule")
        desc_el = rule.find(f"{{{namespace}}}description")
        desc = desc_el.text if desc_el is not None and desc_el.text else ""
        output[rule_id] = (name, desc)
    return output

def load_gst_rule_index() -> dict[str, tuple[str, str]]:
    return load_gst_data()[0]

def get_factions() -> list[tuple[Path, str, str, str, str]]:
    factions: list[tuple[Path, str, str, str, str]] = []
    for file_path in sorted(DATA_DIR.glob("*.cat")):
        try:
            ET.parse(file_path)
        except ET.ParseError:
            continue
        parts = file_path.stem.split(" - ")
        army_group = ARMY_GROUP_REMAP.get(parts[0], "Other")
        if len(parts) >= 3:
            sub_prefix = parts[1]
            short_name = " - ".join(parts[2:])
        elif len(parts) == 2:
            sub_prefix = ""
            short_name = parts[1]
        else:
            sub_prefix = ""
            short_name = parts[0]
        factions.append((file_path, file_path.stem, short_name, army_group, sub_prefix))
    return factions

def group_factions_by_army(factions: list[tuple[Path, str, str, str, str]]) -> list[tuple[str, list[MenuEntry]]]:
    by_army: dict[str, list[tuple[Path, str, str, str, str]]] = {}
    for faction in factions:
        by_army.setdefault(faction[3], []).append(faction)

    ordered: list[tuple[str, list[MenuEntry]]] = []
    for army_name in ARMY_GROUP_ORDER + [g for g in sorted(by_army) if g not in ARMY_GROUP_ORDER]:
        if army_name not in by_army:
            continue
        group_factions = by_army[army_name]

        prefix_counts: dict[str, int] = {}
        for faction in group_factions:
            if faction[4]:
                prefix_counts[faction[4]] = prefix_counts.get(faction[4], 0) + 1

        entries: list[MenuEntry] = []
        seen_prefixes: set[str] = set()
        for faction in group_factions:
            sub_prefix = faction[4]
            if sub_prefix and prefix_counts.get(sub_prefix, 0) > 1:
                if sub_prefix not in seen_prefixes:
                    seen_prefixes.add(sub_prefix)
                    sub_factions = [candidate for candidate in group_factions if candidate[4] == sub_prefix]
                    entries.append(("subgroup", (sub_prefix, sub_factions)))
            else:
                entries.append(("faction", faction))
        ordered.append((army_name, entries))
    return ordered

def parse_pts(entry: ET.Element) -> int | None:
    for cost in entry.findall(f"{{{NS_CAT}}}costs/{{{NS_CAT}}}cost"):
        if cost.get("name") == "pts":
            try:
                value = float(cost.get("value", "0"))
                return int(value) if value >= 0 else None
            except ValueError:
                return None
    return None

def parse_keywords(entry: ET.Element) -> tuple[list[str], list[str], list[str]]:
    type_kws: list[str] = []
    special_kws: list[str] = []
    faction_kws: list[str] = []
    seen_types: set[str] = set()
    seen_specials: set[str] = set()
    seen_factions: set[str] = set()

    for category_link in entry.findall(f"{{{NS_CAT}}}categoryLinks/{{{NS_CAT}}}categoryLink"):
        name = _resolve_category_name(category_link)
        if not name or name in STRUCTURAL_CATEGORY_NAMES:
            continue

        if name.startswith(FACTION_PREFIX):
            faction_name = name[len(FACTION_PREFIX):].strip()
            if faction_name and faction_name not in seen_factions:
                seen_factions.add(faction_name)
                faction_kws.append(faction_name)
        elif name in CATEGORY_PRIORITY:
            if name not in seen_types:
                seen_types.add(name)
                type_kws.append(name)
        else:
            if name not in seen_specials:
                seen_specials.add(name)
                special_kws.append(name)

    return type_kws, special_kws, faction_kws

def get_model_min_count(model_entry: ET.Element) -> int:
    for constraint in model_entry.findall(f"{{{NS_CAT}}}constraints/{{{NS_CAT}}}constraint"):
        if constraint.get("type") == "min":
            try:
                return int(float(constraint.get("value", "1")))
            except ValueError:
                return 1
    return 1

def parse_unit_size(entry: ET.Element) -> tuple[int | None, int | None]:
    for seg in entry.findall(f"{{{NS_CAT}}}selectionEntryGroups/{{{NS_CAT}}}selectionEntryGroup"):
        min_val, max_val = _selection_min_max(seg)
        if min_val is not None or max_val is not None:
            return min_val, max_val
    return None, None

def _selection_min_max(parent: ET.Element) -> tuple[int | None, int | None]:
    min_val: int | None = None
    max_val: int | None = None

    for constraint in parent.findall(f"{{{NS_CAT}}}constraints/{{{NS_CAT}}}constraint"):
        if constraint.get("field") != "selections" or constraint.get("scope") != "parent":
            continue
        try:
            value = int(float(constraint.get("value", "0")))
        except ValueError:
            continue
        if constraint.get("type") == "min":
            min_val = value
        elif constraint.get("type") == "max":
            max_val = value

    return min_val, max_val

def _parse_model_variants(entry: ET.Element) -> list[dict[str, object]]:
    model_entries = [
        model_entry
        for model_entry in entry.findall(f"{{{NS_CAT}}}selectionEntries/{{{NS_CAT}}}selectionEntry")
        if model_entry.get("type") == "model"
    ]
    if len(model_entries) < 2:
        return []

    groups: dict[str, list[dict[str, object]]] = {}
    for model_entry in model_entries:
        full_name = (model_entry.get("name") or "").strip()
        if not full_name:
            continue

        lower = full_name.lower()
        marker = " w/ "
        if marker not in lower:
            continue

        marker_index = lower.index(marker)
        base_name = full_name[:marker_index].strip()
        variant_name = full_name[marker_index + len(marker):].strip()

        _min_sel, max_sel = _selection_min_max(model_entry)
        groups.setdefault(base_name.lower(), []).append({
            "base_name": base_name,
            "full_name": full_name,
            "variant_name": variant_name,
            "max": max_sel,
            "id": model_entry.get("id"),
        })

    candidate_groups = [variants for variants in groups.values() if len(variants) >= 2]
    if not candidate_groups:
        return []

    candidate_groups.sort(key=lambda grp: len(grp), reverse=True)
    chosen = candidate_groups[0]

    return [
        {
            "name": str(v["variant_name"]),
            "full_name": str(v["full_name"]),
            "max": v["max"],
            "id": v["id"],
        }
        for v in chosen
    ]

def resolve_rules_from_infolinks(entry: ET.Element, rule_index: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    seen: set[str] = set()
    direct_info_links = entry.find(f"{{{NS_CAT}}}infoLinks")
    if direct_info_links is None:
        return rules
    for info_link in direct_info_links.findall(f"{{{NS_CAT}}}infoLink"):
        if info_link.get("type") != "rule":
            continue
        rule_id = info_link.get("targetId")
        if not rule_id or rule_id in seen:
            continue
        seen.add(rule_id)
        if rule_id in rule_index:
            rules.append(rule_index[rule_id])
        else:
            rules.append((info_link.get("name", "Unknown Rule"), ""))
    return dedupe_named_text(rules)

def parse_profiles_from_entry(entry: ET.Element) -> tuple[dict[str, str], str | None, list, list, list, list]:
    unit_stats: dict[str, str] = {}
    transport_capacity: str | None = None
    ranged: list[tuple[str, dict]] = []
    melee: list[tuple[str, dict]] = []
    abilities: list[tuple[str, str]] = []
    typed_weapons: list[tuple[str, str, dict]] = []

    direct_unit = None
    for profile in entry.findall(f"{{{NS_CAT}}}profiles/{{{NS_CAT}}}profile"):
        if profile.get("typeName") == "Unit":
            direct_unit = profile
            break
    if direct_unit is not None:
        unit_stats = xml_chars(direct_unit, NS_CAT)

    direct_transport = None
    for profile in entry.findall(f"{{{NS_CAT}}}profiles/{{{NS_CAT}}}profile"):
        if profile.get("typeName") == "Transport":
            direct_transport = profile
            break
    if direct_transport is not None:
        transport_capacity = xml_chars(direct_transport, NS_CAT).get("Capacity")

    seen_ids: set[str] = set()
    for profile in entry.findall(f".//{{{NS_CAT}}}profile"):
        profile_id = profile.get("id")
        if profile_id and profile_id in seen_ids:
            continue
        if profile_id:
            seen_ids.add(profile_id)

        profile_name = profile.get("name", "")
        profile_type = profile.get("typeName", "")
        chars = xml_chars(profile, NS_CAT)

        if profile_type == "Unit" and not unit_stats:
            unit_stats = chars
        elif profile_type == "Transport" and transport_capacity is None:
            transport_capacity = chars.get("Capacity")
        elif profile_type == "Ranged Weapons":
            ranged.append((profile_name, chars))
        elif profile_type == "Melee Weapons":
            melee.append((profile_name, chars))
        elif profile_type not in STAT_PROFILE_TYPES and chars:
            char_keys = set(chars.keys())
            if {"Range", "A", "BS", "S", "AP", "D"}.issubset(char_keys):
                typed_weapons.append((profile_type, profile_name, chars))
            elif {"Range", "A", "WS", "S", "AP", "D"}.issubset(char_keys):
                typed_weapons.append((profile_type, profile_name, chars))
            else:
                text = chars.get("Description") or chars.get("Ability") or next(iter(chars.values()), "")
                abilities.append((profile_name, text or ""))

    return unit_stats, transport_capacity, ranged, melee, dedupe_named_text(abilities), typed_weapons

def parse_detachment_rules(cat_root: ET.Element, rule_index: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    shared_info_groups = cat_root.find(f"{{{NS_CAT}}}sharedInfoGroups")
    if shared_info_groups is None:
        return output

    detachment = None
    for info_group in shared_info_groups.findall(f"{{{NS_CAT}}}infoGroup"):
        if info_group.get("name") == "Detachment Rules":
            detachment = info_group
            break

    if detachment is None:
        return output

    seen: set[str] = set()
    for info_link in detachment.findall(f".//{{{NS_CAT}}}infoLink"):
        if info_link.get("type") != "rule":
            continue
        rule_id = info_link.get("targetId")
        if not rule_id or rule_id in seen:
            continue
        seen.add(rule_id)
        if rule_id in rule_index:
            output.append(rule_index[rule_id])
        else:
            output.append((info_link.get("name", "Unknown Rule"), ""))

    return dedupe_named_text(output)

def collect_catalogue_roots(cat_file: Path) -> list[ET.Element]:
    catalogue_index: dict[str, ET.Element] = {}

    for file_path in DATA_DIR.glob("*.cat"):
        try:
            root = ET.parse(file_path).getroot()
        except ET.ParseError:
            continue
        catalogue_id = root.get("id")
        if catalogue_id:
            catalogue_index[catalogue_id] = root

    try:
        main_root = ET.parse(cat_file).getroot()
    except ET.ParseError:
        return []

    roots: list[ET.Element] = []
    seen_ids: set[str] = set()

    def visit(root: ET.Element) -> None:
        catalogue_id = root.get("id")
        visit_key = catalogue_id or str(id(root))
        if visit_key in seen_ids:
            return
        seen_ids.add(visit_key)
        roots.append(root)
        links_el = root.find(f"{{{NS_CAT}}}catalogueLinks")
        if links_el is None:
            return
        for link in links_el.findall(f"{{{NS_CAT}}}catalogueLink"):
            if link.get("type") != "catalogue":
                continue
            if link.get("importRootEntries") != "true":
                continue
            target_id = link.get("targetId")
            if not target_id:
                continue
            linked_root = catalogue_index.get(target_id)
            if linked_root is not None:
                visit(linked_root)

    visit(main_root)
    return roots

def build_shared_entry_index(catalogue_roots: list[ET.Element]) -> dict[str, ET.Element]:
    index: dict[str, ET.Element] = {}
    for cat_root in catalogue_roots:
        shared = cat_root.find(f"{{{NS_CAT}}}sharedSelectionEntries")
        if shared is None:
            continue
        for entry in shared:
            entry_id = entry.get("id")
            if entry_id and entry_id not in index:
                index[entry_id] = entry
    return index

def _merge_weapon_list(base: list[tuple[str, dict]], extra: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    seen = {name.lower() for name, _ in base}
    result = list(base)
    for name, chars in extra:
        if name.lower() not in seen:
            seen.add(name.lower())
            result.append((name, chars))
    return result

def _collect_linked_profiles(entry: ET.Element, shared_index: dict[str, ET.Element], seen: set[str]) -> tuple[list, list, list, list]:
    extra_ranged: list = []
    extra_melee: list = []
    extra_typed: list = []
    extra_abilities: list = []
    for link in entry.findall(f".//{{{NS_CAT}}}entryLink"):
        if link.get("type") != "selectionEntry":
            continue
        target_id = link.get("targetId")
        if not target_id or target_id in seen:
            continue
        seen.add(target_id)
        linked = shared_index.get(target_id)
        if linked is None or linked.get("type") in ("unit", "model"):
            continue
        _, _, ranged, melee, abilities, typed = parse_profiles_from_entry(linked)
        extra_ranged.extend(ranged)
        extra_melee.extend(melee)
        extra_typed.extend(typed)
        extra_abilities.extend(abilities)
        r2, m2, t2, a2 = _collect_linked_profiles(linked, shared_index, seen)
        extra_ranged.extend(r2)
        extra_melee.extend(m2)
        extra_typed.extend(t2)
        extra_abilities.extend(a2)
    return extra_ranged, extra_melee, extra_typed, extra_abilities

def parse_units(cat_file: Path, gst_rules: dict[str, tuple[str, str]]) -> tuple[list[dict], list[tuple[str, str]]]:
    if not PROFILE_TYPE_COLS and GST_FILE.exists():
        load_gst_data()

    catalogue_roots = collect_catalogue_roots(cat_file)
    if not catalogue_roots:
        return [], []

    main_root = catalogue_roots[0]
    merged_rules = dict(gst_rules)

    for cat_root in catalogue_roots:
        merged_rules.update(parse_rules_index(cat_root, NS_CAT))

    shared_entry_index = build_shared_entry_index(catalogue_roots)
    ACTIVE_CATEGORY_INDEX.clear()
    ACTIVE_CATEGORY_INDEX.update(GST_CATEGORY_INDEX)
    ACTIVE_CATEGORY_INDEX.update(_build_category_index(catalogue_roots, NS_CAT))

    units: list[dict] = []
    seen_entry_ids: set[str] = set()

    for cat_root in catalogue_roots:
        shared_selection_entries = cat_root.find(f"{{{NS_CAT}}}sharedSelectionEntries")
        if shared_selection_entries is None:
            continue

        for entry in shared_selection_entries:
            if entry.tag != f"{{{NS_CAT}}}selectionEntry":
                continue

            entry_id = entry.get("id")
            if entry_id and entry_id in seen_entry_ids:
                continue
            if entry_id:
                seen_entry_ids.add(entry_id)

            entry_type = entry.get("type")
            if entry_type not in ("unit", "model"):
                continue

            unit_name = entry.get("name", "Unknown")
            type_keywords, special_keywords, faction_keywords = parse_keywords(entry)
            unit_pts = parse_pts(entry)
            unit_rules = resolve_rules_from_infolinks(entry, merged_rules)
            unit_min, unit_max = parse_unit_size(entry)
            model_variants = _parse_model_variants(entry)

            model_entries: list[ET.Element] = []
            if entry_type == "unit":
                for selection_entry in entry.findall(f"{{{NS_CAT}}}selectionEntries/{{{NS_CAT}}}selectionEntry"):
                    if selection_entry.get("type") == "model":
                        model_entries.append(selection_entry)

            models: list[dict] = []
            unit_level_abilities: list[tuple[str, str]] = []

            if model_entries:
                for profile in entry.findall(f"{{{NS_CAT}}}profiles/{{{NS_CAT}}}profile"):
                    profile_type = profile.get("typeName", "")
                    if profile_type in STAT_PROFILE_TYPES:
                        continue
                    chars = xml_chars(profile, NS_CAT)
                    if not chars:
                        continue
                    text = chars.get("Description") or chars.get("Ability") or next(iter(chars.values()), "")
                    unit_level_abilities.append((profile.get("name", ""), text or ""))

                unit_level_abilities = dedupe_named_text(unit_level_abilities)

                for model_entry in model_entries:
                    model_count = get_model_min_count(model_entry)
                    model_stats, model_transport_cap, model_ranged, model_melee, model_abilities, model_typed_weapons = parse_profiles_from_entry(model_entry)
                    model_rules = resolve_rules_from_infolinks(model_entry, merged_rules)
                    lnk_r, lnk_m, lnk_t, lnk_a = _collect_linked_profiles(model_entry, shared_entry_index, set())
                    models.append({
                        "name": model_entry.get("name", "Unknown"),
                        "count": model_count,
                        "stats": model_stats,
                        "transport_cap": model_transport_cap,
                        "ranged": _merge_weapon_list(model_ranged, lnk_r),
                        "melee": _merge_weapon_list(model_melee, lnk_m),
                        "typed_weapons": model_typed_weapons + lnk_t,
                        "abilities": dedupe_named_text(model_abilities + lnk_a),
                        "rules": model_rules,
                    })
            else:
                model_stats, model_transport_cap, model_ranged, model_melee, model_abilities, model_typed_weapons = parse_profiles_from_entry(entry)
                model_rules = resolve_rules_from_infolinks(entry, merged_rules)
                lnk_r, lnk_m, lnk_t, lnk_a = _collect_linked_profiles(entry, shared_entry_index, set())
                models.append({
                    "name": unit_name,
                    "count": 1,
                    "stats": model_stats,
                    "transport_cap": model_transport_cap,
                    "ranged": _merge_weapon_list(model_ranged, lnk_r),
                    "melee": _merge_weapon_list(model_melee, lnk_m),
                    "typed_weapons": model_typed_weapons + lnk_t,
                    "abilities": dedupe_named_text(model_abilities + lnk_a),
                    "rules": model_rules,
                })

            warlord_eligible = any(
                el.get("name") == "Warlord"
                for el in entry.findall(f"{{{NS_CAT}}}entryLinks/{{{NS_CAT}}}entryLink")
            )

            leader_targets: list[str] = []
            for ab_name, ab_desc in unit_level_abilities:
                if ab_name == "Leader":
                    leader_targets = parse_leader_targets(ab_desc)
                    break
            if not leader_targets:
                for model_dict in models:
                    for ab_name, ab_desc in model_dict.get("abilities", []):
                        if ab_name == "Leader":
                            leader_targets = parse_leader_targets(ab_desc)
                            break
                    if leader_targets:
                        break

            units.append({
                "id": entry.get("id"),
                "name": unit_name,
                "pts": unit_pts,
                "unit_min": unit_min,
                "unit_max": unit_max,
                "type_keywords": type_keywords,
                "special_keywords": special_keywords,
                "faction_keywords": faction_keywords,
                "rules": dedupe_named_text(unit_rules),
                "unit_abilities": unit_level_abilities,
                "models": models,
                "model_variants": model_variants,
                "warlord_eligible": warlord_eligible,
                "leader_targets": leader_targets,
            })

    units.sort(key=lambda unit: unit["name"])
    faction_rules = parse_detachment_rules(main_root, merged_rules)

    army_rule = next((value for value in merged_rules.values() if value[0] == "Reanimation Protocols"), None)
    if army_rule and all(name != army_rule[0] for name, _ in faction_rules):
        faction_rules.insert(0, army_rule)

    return units, dedupe_named_text(faction_rules)

def parse_leader_targets(description: str) -> list[str]:
    m = _LEADER_HEADER_RE.search(description)
    if not m:
        return []
    body = description[m.end():]
    inline = re.search(r"[\*\^]{2,}(.+?)[\*\^]{2,}", body, re.DOTALL)
    if inline:
        parts = re.split(r"[;,]", inline.group(1))
    else:
        bullet_lines = [ln for ln in body.splitlines() if "■" in ln]
        parts = bullet_lines if bullet_lines else (body.splitlines()[:1] if body.splitlines() else [])
    return [_MARKUP_RE.sub("", p).replace("■", "").strip() for p in parts if _MARKUP_RE.sub("", p).replace("■", "").strip()]

def parse_battle_sizes(root: ET.Element) -> list[tuple[str, int]]:
    battle_sizes: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()

    for entry in root.findall(f".//{{{NS_GST}}}selectionEntry"):
        if entry.get("name") != "Battle Size":
            continue

        for choice in entry.findall(f".//{{{NS_GST}}}selectionEntry"):
            if choice is entry:
                continue

            raw_name = choice.get("name", "").strip()
            if not raw_name:
                continue

            match = _BATTLE_SIZE_PT_RE.search(raw_name)
            if not match:
                continue

            points_limit = int(match.group(1))
            display_name = re.sub(r"^\d+\.\s*", "", raw_name)
            display_name = re.sub(r"\s*\(\d+\s+Point\s+limit\)\s*$", "", display_name, flags=re.IGNORECASE).strip()

            item = (display_name, points_limit)
            if item not in seen:
                seen.add(item)
                battle_sizes.append(item)

    battle_sizes.sort(key=lambda item: item[1])
    return battle_sizes

def load_gst_data() -> tuple[dict[str, tuple[str, str]], list[tuple[str, int]]]:
    if not GST_FILE.exists():
        PROFILE_TYPE_COLS.clear()
        GST_CATEGORY_INDEX.clear()
        ACTIVE_CATEGORY_INDEX.clear()
        STAT_PROFILE_TYPES.clear()
        UNIT_STATS[:] = []
        RANGED_COLS[:] = []
        MELEE_COLS[:] = []
        UNIT_TYPES[:] = []
        return {}, []

    try:
        root = ET.parse(GST_FILE).getroot()
        _refresh_gst_source_metadata(root)
        return parse_rules_index(root, NS_GST), parse_battle_sizes(root)
    except ET.ParseError:
        PROFILE_TYPE_COLS.clear()
        GST_CATEGORY_INDEX.clear()
        ACTIVE_CATEGORY_INDEX.clear()
        STAT_PROFILE_TYPES.clear()
        UNIT_STATS[:] = []
        RANGED_COLS[:] = []
        MELEE_COLS[:] = []
        UNIT_TYPES[:] = []
        return {}, []