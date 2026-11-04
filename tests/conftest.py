import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
HACK = FONTS / "Hack-Regular.ttf"
DEJAVU = os.environ.get("FONTMASK_DEJAVU_SANS")
SOURCE_CODE_PRO = os.environ.get("FONTMASK_SOURCE_CODE_PRO")
ROBOTO_MONO = os.environ.get("FONTMASK_ROBOTO_MONO")


@pytest.fixture(scope="session")
def hack_path():
    return HACK


@pytest.fixture(scope="session")
def dejavu_path():
    if not DEJAVU:
        pytest.skip("FONTMASK_DEJAVU_SANS is not set")
    return Path(DEJAVU)


@pytest.fixture(scope="session")
def source_code_pro_path():
    if not SOURCE_CODE_PRO:
        pytest.skip("FONTMASK_SOURCE_CODE_PRO is not set")
    return Path(SOURCE_CODE_PRO)


@pytest.fixture(scope="session")
def roboto_mono_path():
    if not ROBOTO_MONO:
        pytest.skip("FONTMASK_ROBOTO_MONO is not set")
    return Path(ROBOTO_MONO)
