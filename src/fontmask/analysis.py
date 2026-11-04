"""Target-font inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from .rules import RuleSet


@dataclass
class Analysis:
    outlines: str
    variable: bool
    monospace: bool
    upm: int
    glyph_count: int
    cmap_count: int
    features: list[str] = field(default_factory=list)
    has_ccmp: bool = False
    already_masked: bool = False
    referenced: int = 0
    encoded_present: int = 0
    encoded_missing: list[str] = field(default_factory=list)
    specials: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "outlines": self.outlines,
            "variable": self.variable,
            "monospace": self.monospace,
            "upm": self.upm,
            "glyph_count": self.glyph_count,
            "cmap_count": self.cmap_count,
            "features": self.features,
            "has_ccmp": self.has_ccmp,
            "already_masked": self.already_masked,
            "referenced": self.referenced,
            "encoded_present": self.encoded_present,
            "encoded_missing": self.encoded_missing,
            "specials": self.specials,
        }


def analyze(font, rules: RuleSet) -> Analysis:
    if "CFF " in font:
        outlines = "CFF"
    elif "CFF2" in font:
        outlines = "CFF2"
    elif "glyf" in font:
        outlines = "TrueType"
    else:
        outlines = "unknown"

    widths = {width for width, _ in font["hmtx"].metrics.values() if width}
    fixed_pitch = bool(font["post"].isFixedPitch) if "post" in font else False
    monospace = fixed_pitch or len(widths) <= 1
    cmap = font.getBestCmap() or {}
    glyph_set = set(font.getGlyphOrder())
    features: list[str] = []
    has_ccmp = False
    if "GSUB" in font:
        for record in font["GSUB"].table.FeatureList.FeatureRecord:
            features.append(record.FeatureTag)
            if record.FeatureTag == "ccmp":
                has_ccmp = True

    analysis = Analysis(
        outlines=outlines,
        variable="fvar" in font,
        monospace=monospace,
        upm=cast(Any, font["head"]).unitsPerEm,
        glyph_count=font["maxp"].numGlyphs,
        cmap_count=len(cmap),
        features=sorted(set(features)),
        has_ccmp=has_ccmp,
        already_masked=any(name.startswith("secret.mask") for name in glyph_set),
    )

    for name in sorted(rules.referenced):
        if name in rules.mask_classes:
            continue
        analysis.referenced += 1
        if name in glyph_set:
            analysis.encoded_present += 1
            continue
        codepoint = rules.inverse_cmap.get(name)
        if codepoint is not None:
            if codepoint in cmap:
                analysis.encoded_present += 1
            else:
                analysis.encoded_missing.append(name)
        else:
            analysis.specials.append(name)
    return analysis
