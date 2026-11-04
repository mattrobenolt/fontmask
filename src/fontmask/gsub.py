"""GSUB surgery: rename, remap, width-bucket, and merge the mask lookups."""

from __future__ import annotations

import copy

from fontTools.ttLib import newTable
from fontTools.ttLib.tables import otTables as ot

from .rules import walk


def rename_lookups(lookups, mapping: dict[str, str]) -> None:
    def replace(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, tuple):
            return tuple(replace(item) for item in value)
        if isinstance(value, dict):
            return {replace(key): replace(item) for key, item in value.items()}
        if hasattr(value, "__dict__") and not isinstance(value, (bytes, bytearray)):
            for key, item in list(vars(value).items()):
                setattr(value, key, replace(item))
            return value
        return value

    for lookup in lookups:
        replace(lookup)


def remap_lookup_records(lookups, local_index: dict[int, int], offset: int) -> None:
    for lookup in lookups:
        for obj in walk(lookup):
            if isinstance(obj, ot.SubstLookupRecord):
                if obj.LookupListIndex not in local_index:
                    raise ValueError(f"nested lookup {obj.LookupListIndex} is outside the rule closure")
                obj.LookupListIndex = offset + local_index[obj.LookupListIndex]


def _expand_coverage(coverage, mask_classes, width_variants) -> None:
    if coverage is None:
        return
    expanded = []
    for name in coverage.glyphs:
        if name in mask_classes:
            expanded.extend(width_variants[name].values())
        else:
            expanded.append(name)
    coverage.glyphs = list(dict.fromkeys(expanded))


def _expand_classdef(classdef, mask_classes, width_variants) -> None:
    if classdef is None:
        return
    for name in list(classdef.classDefs):
        if name in mask_classes:
            klass = classdef.classDefs.pop(name)
            for variant in width_variants[name].values():
                classdef.classDefs[variant] = klass


def rewrite_mask_widths(lookups, mask_classes, width_variants, target_widths) -> None:
    for lookup in lookups:
        for subtable in lookup.SubTable:
            real = subtable.ExtSubTable if lookup.LookupType == 7 else subtable
            mapping = getattr(real, "mapping", None)
            if mapping is not None:
                for source in list(mapping):
                    target = mapping[source]
                    if source in mask_classes:
                        widths = width_variants[source]
                        del mapping[source]
                        for width, source_variant in widths.items():
                            out = target
                            if target in mask_classes:
                                out = width_variants[target][width]
                            mapping[source_variant] = out
                    elif target in mask_classes:
                        width = target_widths[source]
                        mapping[source] = width_variants[target][width]
                continue

            if lookup.LookupType not in (6, 7):
                raise ValueError(
                    f"unsupported GSUB lookup type {lookup.LookupType}; the rule set expects types 1, 6, and 7"
                )

            for obj in walk(real):
                if isinstance(obj, ot.Coverage):
                    _expand_coverage(obj, mask_classes, width_variants)
                elif isinstance(obj, ot.ClassDef):
                    _expand_classdef(obj, mask_classes, width_variants)

    for lookup in lookups:
        for obj in walk(lookup):
            if isinstance(obj, str) and obj in mask_classes:
                raise ValueError(f"unexpanded mask glyph reference: {obj}")


def sort_coverages(lookups, glyph_id: dict[str, int]) -> None:
    for lookup in lookups:
        for obj in walk(lookup):
            if isinstance(obj, ot.Coverage):
                obj.glyphs.sort(key=lambda name: glyph_id[name])


def _new_langsys() -> ot.LangSys:
    langsys = ot.LangSys()
    langsys.LookupOrder = None
    langsys.ReqFeatureIndex = 0xFFFF
    langsys.FeatureIndex = []
    langsys.FeatureCount = 0
    return langsys


def _new_script() -> ot.Script:
    script = ot.Script()
    script.DefaultLangSys = _new_langsys()
    script.LangSysRecord = []
    return script


def ensure_gsub(font):
    if "GSUB" in font:
        return font["GSUB"].table

    gsub = ot.GSUB()
    gsub.Version = 0x00010000
    gsub.ScriptList = ot.ScriptList()
    gsub.ScriptList.ScriptRecord = []
    gsub.FeatureList = ot.FeatureList()
    gsub.FeatureList.FeatureRecord = []
    gsub.LookupList = ot.LookupList()
    gsub.LookupList.Lookup = []

    table = newTable("GSUB")
    table.table = gsub
    font["GSUB"] = table
    return gsub


def _register_feature(gsub, feature_index: int) -> None:
    scripts = gsub.ScriptList.ScriptRecord
    if not scripts:
        record = ot.ScriptRecord()
        record.ScriptTag = "DFLT"
        record.Script = _new_script()
        scripts.append(record)

    for record in scripts:
        script = record.Script
        if script.DefaultLangSys is None:
            script.DefaultLangSys = _new_langsys()
        if feature_index not in script.DefaultLangSys.FeatureIndex:
            script.DefaultLangSys.FeatureIndex.append(feature_index)
        script.DefaultLangSys.FeatureCount = len(script.DefaultLangSys.FeatureIndex)
        for lang in script.LangSysRecord:
            langsys = lang.LangSys
            if feature_index not in langsys.FeatureIndex:
                langsys.FeatureIndex.append(feature_index)
            langsys.FeatureCount = len(langsys.FeatureIndex)


def add_ccmp_feature(gsub, lookup_indices: list[int]) -> int:
    existing = []
    for index, record in enumerate(gsub.FeatureList.FeatureRecord):
        if record.FeatureTag == "ccmp":
            for lookup_index in lookup_indices:
                if lookup_index not in record.Feature.LookupListIndex:
                    record.Feature.LookupListIndex.append(lookup_index)
            record.Feature.LookupCount = len(record.Feature.LookupListIndex)
            existing.append(index)
    if existing:
        for index in existing:
            _register_feature(gsub, index)
        return existing[0]

    feature = ot.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = list(lookup_indices)
    feature.LookupCount = len(feature.LookupListIndex)
    record = ot.FeatureRecord()
    record.FeatureTag = "ccmp"
    record.Feature = feature
    index = len(gsub.FeatureList.FeatureRecord)
    gsub.FeatureList.FeatureRecord.append(record)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    _register_feature(gsub, index)
    return index


def merge_gsub(font, lookups, top_local_ids: list[int]) -> int:
    gsub = ensure_gsub(font)
    offset = len(gsub.LookupList.Lookup)
    gsub.LookupList.Lookup.extend(lookups)
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    add_ccmp_feature(gsub, [offset + index for index in top_local_ids])
    gsub.ScriptList.ScriptCount = len(gsub.ScriptList.ScriptRecord)
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    return offset
