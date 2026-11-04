"""Orchestrate the font patching process."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from . import names
from .analysis import Analysis, analyze
from .glyphs import Backend, make_backend
from .gsub import (
    ensure_gsub,
    merge_gsub,
    remap_lookup_records,
    rename_lookups,
    rewrite_mask_widths,
    sort_coverages,
)
from .rules import RuleSet


@dataclass
class Plan:
    analysis: Analysis
    name_map: dict[str, str]
    added: list[str] = field(default_factory=list)
    width_variants: dict[str, dict[int, str]] = field(default_factory=dict)
    target_widths: dict[str, int] = field(default_factory=dict)
    placeholders: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    family: str = ""
    style: str = ""
    instance: dict[str, float] = field(default_factory=dict)

    @property
    def note_count(self) -> int:
        return len(self.added) - sum(len(v) for v in self.width_variants.values())

    @property
    def mask_count(self) -> int:
        return sum(len(v) for v in self.width_variants.values())

    def summary(self) -> dict:
        return {
            "family": self.family,
            "style": self.style,
            "instance": self.instance,
            "glyphs_added": len(self.added),
            "note_glyphs": self.note_count,
            "mask_glyphs": self.mask_count,
            "mask_widths": {
                name: sorted(widths) for name, widths in self.width_variants.items()
            },
            "warnings": self.warnings,
        }


def _new_placeholder(
    backend: Backend,
    name: str,
    warnings: list[str],
    placeholders: set[str],
    reason: str,
) -> str:
    unique = backend.unique_name(name)
    backend.add_empty(unique, 0)
    placeholders.add(unique)
    warnings.append(f"{reason}: {name} -> empty glyph {unique}")
    return unique


def build_plan(
    font,
    rules: RuleSet,
    backend: Backend,
    family: str | None = None,
    style: str | None = None,
) -> Plan:
    analysis = analyze(font, rules)
    if analysis.already_masked:
        raise ValueError(
            "font already contains secret.mask glyphs; refusing to patch twice"
        )

    target_cmap = font.getBestCmap() or {}
    target_glyphs = set(font.getGlyphOrder())
    name_map: dict[str, str] = {}
    warnings: list[str] = []
    added: list[str] = []
    placeholders: set[str] = set()

    # Pass 1: names that already exist, or that have a Unicode codepoint.
    for source in sorted(rules.referenced):
        if source in rules.mask_classes:
            name_map[source] = source
            continue
        if source in target_glyphs:
            name_map[source] = source
            continue
        codepoint = rules.inverse_cmap.get(source)
        if codepoint is None:
            continue
        if codepoint in target_cmap:
            name_map[source] = target_cmap[codepoint]
            continue
        new = _new_placeholder(
            backend,
            f"uni{codepoint:04X}" if codepoint <= 0xFFFF else f"u{codepoint:05X}",
            warnings,
            placeholders,
            "target lacks encoded glyph",
        )
        name_map[source] = new
        added.append(new)

    # Pass 2: note and variant glyphs with no Unicode codepoint.
    for source in sorted(rules.referenced):
        if source in name_map or source in rules.mask_classes:
            continue
        base = rules.base_for(source)
        if base is None:
            new = _new_placeholder(
                backend, source, warnings, placeholders, "no visible base glyph"
            )
            name_map[source] = new
            added.append(new)
            continue
        base_target = name_map.get(base)
        if base_target is None:
            codepoint = rules.inverse_cmap.get(base)
            if codepoint is not None and codepoint in target_cmap:
                base_target = target_cmap[codepoint]
            elif base == ".notdef" and ".notdef" in target_glyphs:
                base_target = ".notdef"
            else:
                base_target = _new_placeholder(
                    backend, base, warnings, placeholders, "missing base glyph"
                )
                added.append(base_target)
        new = backend.unique_name(source)
        backend.add_copy(new, base_target)
        name_map[source] = new
        added.append(new)
        if base_target in placeholders:
            placeholders.add(new)

    # Width of every target glyph the rules can reach.
    target_widths = {
        name: backend.width(name)
        for name in set(name_map.values())
        if name in backend.glyph_set
    }

    # One dot per (mask class, advance width). This preserves line width in
    # proportional fonts and collapses to one dot per class in monospaced fonts.
    width_variants: dict[str, dict[int, str]] = {}
    for mask_class in sorted(rules.mask_classes):
        sources = rules.mask_sources.get(mask_class, set())
        widths: set[int] = set()
        for source in sources:
            target = name_map.get(source)
            if target is None:
                warnings.append(f"mask source {source} has no target glyph; skipping")
                continue
            if target in placeholders:
                width = backend.default_width
            else:
                width = target_widths.get(target, 0)
                if width <= 0:
                    width = backend.default_width
                    warnings.append(
                        f"mask source {source} has zero width; using {width}"
                    )
            target_widths[target] = width
            widths.add(width)
        if not widths:
            continue
        variants: dict[int, str] = {}
        for width in sorted(widths):
            new = backend.unique_name(f"{mask_class}.w{width}")
            backend.add_dot(new, width, rules)
            variants[width] = new
            added.append(new)
        width_variants[mask_class] = variants

    resolved_family, resolved_style = names.patch_metadata(font, family, style)
    return Plan(
        analysis=analysis,
        name_map=name_map,
        added=added,
        width_variants=width_variants,
        target_widths=target_widths,
        placeholders=placeholders,
        warnings=warnings,
        family=resolved_family,
        style=resolved_style,
    )


def apply_plan(font, rules: RuleSet, plan: Plan) -> None:
    lookups = rules.copy_lookups()
    rename_lookups(lookups, plan.name_map)
    rewrite_mask_widths(
        lookups,
        rules.mask_classes,
        plan.width_variants,
        plan.target_widths,
    )

    gsub = ensure_gsub(font)
    offset = len(gsub.LookupList.Lookup)
    remap_lookup_records(lookups, rules.local_index, offset)

    glyph_id = {name: index for index, name in enumerate(font.getGlyphOrder())}
    sort_coverages(lookups, glyph_id)

    top_local = [rules.local_index[index] for index in rules.top_ids]
    merge_gsub(font, lookups, top_local)
    names.patch_metadata(font, plan.family, plan.style)
    names.remove_dsig(font)


def _parse_instance(font, value: str) -> dict[str, float]:
    if not value:
        return {}
    if "=" in value:
        axes: dict[str, float] = {}
        for item in value.split(","):
            key, raw = item.split("=", 1)
            axes[key.strip()] = float(raw)
        return axes

    fvar = font["fvar"]
    for instance in fvar.instances:
        name = font["name"].getDebugName(instance.subfamilyNameID)
        if name and name.lower() == value.lower():
            return {
                axis.axisTag: instance.coordinates[axis.axisTag] for axis in fvar.axes
            }
    raise ValueError(
        f"unknown instance {value!r}; use axis=value pairs or a named instance"
    )


def patch_font(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    family: str | None = None,
    style: str | None = None,
    instance: str | None = None,
    rules_path: str | Path | None = None,
    font_number: int = 0,
    dry_run: bool = False,
) -> Plan:
    input_path = Path(input_path)
    output_path = (
        Path(output_path)
        if output_path
        else input_path.with_name(f"{input_path.stem}-masked{input_path.suffix}")
    )
    rules = RuleSet.load(rules_path)
    font = TTFont(input_path, fontNumber=font_number)

    axes = _parse_instance(font, instance or "") if "fvar" in font else {}
    was_variable = "fvar" in font
    explicit_instance = bool(axes)
    if was_variable:
        if not axes:
            axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
        instantiateVariableFont(font, axes, inplace=True, updateFontNames=False)

    backend = make_backend(font)
    plan = build_plan(font, rules, backend, family=family, style=style)
    plan.instance = axes
    if was_variable and not explicit_instance:
        plan.warnings.append("variable font instanced at the default axes")

    if dry_run:
        return plan

    apply_plan(font, rules, plan)

    suffix = output_path.suffix.lower()
    if suffix == ".woff2":
        font.flavor = "woff2"
    elif suffix == ".woff":
        font.flavor = "woff"
    else:
        font.flavor = None

    backend.finish()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(output_path)
    return plan
