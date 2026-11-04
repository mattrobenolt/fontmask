from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


def test_cff_patch(source_code_pro_path, tmp_path):
    out = tmp_path / "SourceCodeProMasked.otf"
    plan = patch_font(source_code_pro_path, out)
    assert out.exists()
    assert plan.analysis.outlines == "CFF"
    assert plan.mask_count == 19

    font = TTFont(out)
    assert "CFF " in font
    names, _ = shape(out, "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB")
    assert any(is_mask(name) for name in names)
    assert sum(1 for name in names if is_mask(name)) == 12
