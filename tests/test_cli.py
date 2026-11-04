import json

from fontmask.cli import main


def test_inspect_json(hack_path, capsys):
    assert main(["inspect", str(hack_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outlines"] == "TrueType"
    assert data["monospace"] is True
    assert data["already_masked"] is False


def test_patch_dry_run(hack_path, capsys):
    assert main(["patch", str(hack_path), "--dry-run", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["family"] == "Hack Masked"
    assert data["mask_glyphs"] == 19


def test_patch_writes(hack_path, tmp_path):
    out = tmp_path / "HackMasked.ttf"
    assert main(["patch", str(hack_path), "-o", str(out)]) == 0
    assert out.exists()
