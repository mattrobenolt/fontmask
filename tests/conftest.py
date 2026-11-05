import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
HACK = FONTS / "Hack-Regular.ttf"


def _fixture_font(env_var, filename):
    value = os.environ.get(env_var)
    if value:
        return Path(value)
    return FONTS / filename


DEJAVU = _fixture_font("FONTMASK_DEJAVU_SANS", "DejaVuSans.ttf")
SOURCE_CODE_PRO = _fixture_font(
    "FONTMASK_SOURCE_CODE_PRO", "SourceCodePro-Regular.otf"
)
ROBOTO_MONO = _fixture_font("FONTMASK_ROBOTO_MONO", "RobotoMono[wght].ttf")


@pytest.fixture(scope="session")
def hack_path():
    return HACK


@pytest.fixture(scope="session")
def dejavu_path():
    if not DEJAVU.exists():
        pytest.skip(f"missing test font: {DEJAVU}")
    return DEJAVU


@pytest.fixture(scope="session")
def source_code_pro_path():
    if not SOURCE_CODE_PRO.exists():
        pytest.skip(f"missing test font: {SOURCE_CODE_PRO}")
    return SOURCE_CODE_PRO


@pytest.fixture(scope="session")
def roboto_mono_path():
    if not ROBOTO_MONO.exists():
        pytest.skip(f"missing test font: {ROBOTO_MONO}")
    return ROBOTO_MONO
