import random
import string
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font
from fontmask.rules import RuleSet

from .helpers import is_mask, shape
from .fixtures import tests as literal_tests


SECRET = "ghp_aB3dEFGHiJ7kLmN0pQr"


def test_patch_hack(hack_path, tmp_path):
    out = tmp_path / "HackMasked.ttf"
    plan = patch_font(hack_path, out)
    assert out.exists()
    assert plan.family == "Hack Masked"
    assert plan.mask_count == 19
    assert plan.note_count > 250

    font = TTFont(out)
    assert font["name"].getDebugName(1) == "Hack Masked"
    assert font["name"].getDebugName(4) == "Hack Masked"
    assert "secret.mask.alnum.w1233" in font.getGlyphOrder()
    assert "DSIG" not in font

    names, advances = shape(out, SECRET)
    assert names[:4] == ["uni0067", "uni0068", "uni0070", "underscore.sec.alnum.lower"]
    assert names[4:8] == ["uni0061", "uni0042", "uni0033", "uni0064"]
    assert all(is_mask(name) for name in names[8:])
    assert len(set(advances)) == 1


def test_normal_text_unchanged(hack_path, tmp_path):
    out = tmp_path / "HackMasked.ttf"
    patch_font(hack_path, out)
    for text in [
        "MONKEY=banana",
        "SORT_KEY=modified_date",
        "ghp_import",
        "pk_live_51HxT7vLm3NaZ81kPq0",
    ]:
        before, before_advances = shape(hack_path, text)
        after, after_advances = shape(out, text)
        assert before_advances == after_advances, text
        assert len(before) == len(after), text
        assert not any(is_mask(name) for name in after), text


def test_parity_with_obel(hack_path, tmp_path):
    out = tmp_path / "HackMasked.ttf"
    patch_font(hack_path, out)
    rules = RuleSet.load()
    obel = rules.font
    obel_inv = {name: cp for cp, name in (obel.getBestCmap() or {}).items()}
    hack_cmap = TTFont(out).getBestCmap() or {}

    def normalize_obel(name):
        if is_mask(name):
            return "MASK"
        cp = obel_inv.get(name)
        if cp is not None and cp in hack_cmap:
            return hack_cmap[cp]
        return name

    def normalize_patched(name):
        return "MASK" if is_mask(name) else name

    cases = list(literal_tests)
    random.seed(1)
    alphabet = string.ascii_letters + string.digits + "_-./+="
    contexts = [
        "ghp_",
        "sk-ant-",
        "AKIA",
        "GITHUB_TOKEN=",
        "API_KEY=",
        "password",
        '"token": "',
        "--api-key=",
        "Authorization: Bearer ",
    ]
    for context in contexts:
        for _ in range(40):
            cases.append(
                context
                + "".join(random.choice(alphabet) for _ in range(random.randint(0, 30)))
            )

    for text in cases:
        before, _ = shape(rule_path(), text)
        after, _ = shape(out, text)
        assert [normalize_obel(name) for name in before] == [
            normalize_patched(name) for name in after
        ], text


def rule_path():
    from fontmask.rules import DEFAULT_RULES_FONT

    return DEFAULT_RULES_FONT


def test_refuses_double_patch(hack_path, tmp_path):
    out = tmp_path / "HackMasked.ttf"
    patch_font(hack_path, out)
    with pytest.raises(ValueError):
        patch_font(out, tmp_path / "again.ttf")
