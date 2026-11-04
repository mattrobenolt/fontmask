from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


def test_variable_instance(roboto_mono_path, tmp_path):
    out = tmp_path / "RobotoMonoMasked.ttf"
    plan = patch_font(roboto_mono_path, out, instance="wght=400")
    assert plan.instance == {"wght": 400.0}
    font = TTFont(out)
    assert "fvar" not in font
    assert "gvar" not in font
    names, _ = shape(out, "ghp_aB3dEFGHiJ7kLmN0pQr")
    assert any(is_mask(name) for name in names)


def test_variable_default_instance(roboto_mono_path, tmp_path):
    out = tmp_path / "RobotoMonoDefault.ttf"
    plan = patch_font(roboto_mono_path, out)
    assert plan.instance == {"wght": 400.0}
    font = TTFont(out)
    assert "fvar" not in font
    names, _ = shape(out, "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB")
    assert any(is_mask(name) for name in names)
