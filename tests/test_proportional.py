from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


SAMPLES = [
    "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB",
    "ghp_aB3dEFGHiJ7kLmN0pQr",
    "Authorization: Bearer aZ81kPq0xT7vLm3N",
    "MONKEY=banana",
]


def test_proportional_preserves_advances(dejavu_path, tmp_path):
    out = tmp_path / "DejaVuSansMasked.ttf"
    plan = patch_font(dejavu_path, out)
    assert plan.analysis.monospace is False
    assert plan.mask_count > 19

    font = TTFont(out)
    for source_name, target_name in plan.name_map.items():
        if source_name in plan.width_variants:
            continue
    for text in SAMPLES:
        before, before_advances = shape(dejavu_path, text)
        after, after_advances = shape(out, text)
        assert before_advances == after_advances, text
        assert len(before) == len(after), text

    names, _ = shape(out, SAMPLES[0])
    assert any(is_mask(name) for name in names)
    assert sum(1 for name in names if is_mask(name)) == 12


def test_mask_advance_matches_source(dejavu_path, tmp_path):
    out = tmp_path / "DejaVuSansMasked.ttf"
    plan = patch_font(dejavu_path, out)
    font = TTFont(out)
    for mask_class, variants in plan.width_variants.items():
        for width, glyph_name in variants.items():
            assert font["hmtx"][glyph_name][0] == width
