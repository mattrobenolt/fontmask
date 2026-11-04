"""Name-table and metadata updates for the patched font."""

from __future__ import annotations

import re

from fontTools.ttLib.tables._n_a_m_e import NameRecord

OBEL_NOTICE = (
    "This font includes secret-masking rules from Obel Mono, "
    "Copyright 2026 The Obel Mono Project Authors, licensed under the "
    "SIL Open Font License 1.1."
)
OBEL_COPYRIGHT = "Mask rules: Copyright 2026 The Obel Mono Project Authors."
OFL_URL = "https://openfontlicense.org"


def get_name(font, name_id: int, default: str | None = None) -> str | None:
    for record in font["name"].names:
        if record.nameID == name_id:
            try:
                return record.toUnicode()
            except Exception:
                continue
    return default


def _set_existing(font, name_id: int, value: str) -> None:
    found = False
    for record in font["name"].names:
        if record.nameID == name_id:
            record.string = value
            found = True
    if not found:
        record = NameRecord()
        record.nameID = name_id
        record.platformID = 3
        record.platEncID = 1
        record.langID = 0x409
        record.string = value
        font["name"].names.append(record)


def _sanitize_ps(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9-]", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:63] or "FontMasked-Regular"


def patch_metadata(font, family: str | None = None, style: str | None = None) -> tuple[str, str]:
    original_family = get_name(font, 16) or get_name(font, 1) or "Untitled"
    original_style = get_name(font, 17) or get_name(font, 2) or "Regular"
    family = family or f"{original_family} Masked"
    style = style or original_style

    _set_existing(font, 1, family)
    _set_existing(font, 2, style)
    _set_existing(font, 4, f"{family} {style}" if style.lower() != "regular" else family)
    _set_existing(font, 6, _sanitize_ps(f"{family}-{style}"))
    _set_existing(font, 16, family)
    _set_existing(font, 17, style)
    _set_existing(font, 3, f"{family}: {style}: 2026; fontmask")

    copyright_text = get_name(font, 0)
    if copyright_text and OBEL_COPYRIGHT not in copyright_text:
        _set_existing(font, 0, f"{copyright_text} / {OBEL_COPYRIGHT}")
    elif not copyright_text:
        _set_existing(font, 0, OBEL_COPYRIGHT)

    license_text = get_name(font, 13) or ""
    if OBEL_NOTICE not in license_text:
        _set_existing(font, 13, (license_text.rstrip() + "\n\n" + OBEL_NOTICE).strip())
    _set_existing(font, 14, OFL_URL)
    return family, style


def remove_dsig(font) -> None:
    if "DSIG" in font:
        del font["DSIG"]
