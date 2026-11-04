from fontTools.ttLib import TTFont

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


def test_creates_gsub(hack_path, tmp_path):
    stripped = tmp_path / "HackNoGSUB.ttf"
    font = TTFont(hack_path)
    del font["GSUB"]
    font.save(stripped)

    out = tmp_path / "HackNoGSUBMasked.ttf"
    patch_font(stripped, out)
    patched = TTFont(out)
    assert "GSUB" in patched
    assert any(record.FeatureTag == "ccmp" for record in patched["GSUB"].table.FeatureList.FeatureRecord)
    names, _ = shape(out, "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB")
    assert any(is_mask(name) for name in names)
