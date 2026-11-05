import pytest

from fontmask.patcher import patch_font

from .helpers import is_mask, shape


CASES = [
    ("LEARNING_TRIGGER_SECRET", "A" * 64),
    ("DIAGNOSTICS_SECRET", "B" * 64),
    ("AGENT_AWS_SECRET_ACCESS_KEY", "C" * 40),
    ("SERVICE_API_KEY", "D" * 108),
]


@pytest.mark.parametrize("name,value", CASES)
def test_exported_env_names(hack_path, tmp_path, name, value):
    out = tmp_path / "HackMasked.ttf"
    patch_font(hack_path, out)

    text = f"export {name}={value}"
    glyphs, _ = shape(out, text)
    assert sum(1 for glyph in glyphs if is_mask(glyph)) == len(value) - 4
