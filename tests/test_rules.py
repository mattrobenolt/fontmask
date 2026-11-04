from fontmask.rules import RuleSet


def test_rule_closure():
    rules = RuleSet.load()
    assert len(rules.lookups) == 108
    assert len(rules.referenced) == 700
    assert len(rules.mask_classes) == 19
    assert rules.dot_name == "secret.mask.alnum"


def test_base_resolution():
    rules = RuleSet.load()
    assert rules.base_for("underscore.sec.alnum.lower") == "underscore"
    assert rules.base_for("one.plain.sec.ui") == "one"
    assert rules.base_for("A.sec.upper") == "A"
    assert rules.base_for("a.ductus.sec.ui") == "a"
    assert rules.base_for(".notdef") == ".notdef"
    assert rules.base_for("secret.mask.alnum") is None


def test_every_mask_class_has_sources():
    rules = RuleSet.load()
    for mask_class in rules.mask_classes:
        assert rules.mask_sources.get(mask_class), mask_class
