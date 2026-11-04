"""Load the secret-masking rule set from the bundled Obel Mono Masked font."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_RULES_FONT = DATA_DIR / "ObelMonoMasked-Regular.ttf"


def walk(obj, seen: set[int] | None = None):
    """Yield every object in a fontTools table tree once."""
    if seen is None:
        seen = set()
    if id(obj) in seen:
        return
    seen.add(id(obj))
    yield obj
    if isinstance(obj, (list, tuple)):
        for item in obj:
            yield from walk(item, seen)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(key, seen)
            yield from walk(value, seen)
    elif hasattr(obj, "__dict__"):
        for value in vars(obj).values():
            yield from walk(value, seen)


def _closure(gsub, top_ids):
    from collections import deque

    queue = deque(top_ids)
    seen: set[int] = set()
    while queue:
        index = queue.popleft()
        if index in seen:
            continue
        seen.add(index)
        lookup = gsub.LookupList.Lookup[index]
        for subtable in lookup.SubTable:
            for obj in walk(subtable):
                if isinstance(obj, ot.SubstLookupRecord):
                    queue.append(obj.LookupListIndex)
    return sorted(seen)


def _strings_in(obj, allowed: set[str]) -> set[str]:
    return {item for item in walk(obj) if isinstance(item, str) and item in allowed}


@dataclass
class RuleSet:
    font: TTFont
    lookups: list
    closure_ids: list[int]
    top_ids: list[int]
    local_index: dict[int, int]
    referenced: set[str]
    mask_classes: set[str]
    mask_sources: dict[str, set[str]]
    dot_name: str
    dot_recording: DecomposingRecordingPen
    dot_bounds: tuple[float, float, float, float]
    upm: int
    cmap: dict[int, str]
    inverse_cmap: dict[str, int]
    glyph_set: set[str]
    glyph_order: list[str]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "RuleSet":
        path = Path(path) if path else DEFAULT_RULES_FONT
        font = TTFont(path)
        gsub = font["GSUB"].table
        feature = next(
            record.Feature
            for record in gsub.FeatureList.FeatureRecord
            if record.FeatureTag == "ccmp"
        )
        top_ids = list(feature.LookupListIndex)
        closure_ids = _closure(gsub, top_ids)
        local_index = {old: new for new, old in enumerate(closure_ids)}
        lookups = [copy.deepcopy(gsub.LookupList.Lookup[i]) for i in closure_ids]

        glyph_order = font.getGlyphOrder()
        glyph_set = set(glyph_order)
        referenced: set[str] = set()
        for lookup in lookups:
            referenced |= _strings_in(lookup, glyph_set)

        mask_classes = {name for name in referenced if name.startswith("secret.mask")}
        mask_sources: dict[str, set[str]] = {}
        for lookup in lookups:
            for subtable in lookup.SubTable:
                real = subtable.ExtSubTable if lookup.LookupType == 7 else subtable
                mapping = getattr(real, "mapping", None)
                if not mapping:
                    continue
                for source, target in mapping.items():
                    if target in mask_classes:
                        mask_sources.setdefault(target, set()).add(source)

        dot_name = "secret.mask.alnum" if "secret.mask.alnum" in mask_classes else sorted(mask_classes)[0]
        glyph_set_obj = font.getGlyphSet()
        dot_recording = DecomposingRecordingPen(glyph_set_obj)
        glyph_set_obj[dot_name].draw(dot_recording)
        bounds_pen = BoundsPen(glyph_set_obj)
        glyph_set_obj[dot_name].draw(bounds_pen)
        if bounds_pen.bounds is None:
            raise ValueError(f"rules font dot glyph {dot_name!r} has no bounds")

        cmap = font.getBestCmap()
        inverse_cmap = {name: cp for cp, name in cmap.items()}
        return cls(
            font=font,
            lookups=lookups,
            closure_ids=closure_ids,
            top_ids=top_ids,
            local_index=local_index,
            referenced=referenced,
            mask_classes=mask_classes,
            mask_sources=mask_sources,
            dot_name=dot_name,
            dot_recording=dot_recording,
            dot_bounds=tuple(bounds_pen.bounds),
            upm=font["head"].unitsPerEm,
            cmap=cmap,
            inverse_cmap=inverse_cmap,
            glyph_set=glyph_set,
            glyph_order=glyph_order,
        )

    def copy_lookups(self):
        return copy.deepcopy(self.lookups)

    def is_mask(self, name: str) -> bool:
        return name in self.mask_classes

    def base_for(self, name: str) -> str | None:
        """Find the visible source glyph behind a note or variant glyph name."""
        base = name
        if base == ".notdef":
            return ".notdef"
        if ".ductus" in base:
            base = base.split(".ductus")[0]
        for marker in (".sec", ".mask"):
            if marker in base:
                base = base.split(marker)[0]
        while base and base not in self.inverse_cmap and "." in base:
            base = base.rsplit(".", 1)[0]
        if base == ".notdef":
            return ".notdef"
        if base in self.inverse_cmap:
            return base
        return None

    def is_special(self, name: str) -> bool:
        """True when the name has no Unicode codepoint in the rules font."""
        return name not in self.inverse_cmap
