from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


def test_woff2_round_trip(hack_path, tmp_path):
    woff2 = tmp_path / "Hack.woff2"
    font = TTFont(hack_path)
    font.flavor = "woff2"
    font.save(woff2)

    out = tmp_path / "HackMasked.woff2"
    patch_font(woff2, out)
    masked = TTFont(out)
    assert masked.flavor == "woff2"
    assert any(name.startswith("secret.mask") for name in masked.getGlyphOrder())

    ttf = tmp_path / "HackMasked.ttf"
    masked.flavor = None
    masked.save(ttf)
    names, _ = shape(ttf, "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB")
    assert any(is_mask(name) for name in names)
