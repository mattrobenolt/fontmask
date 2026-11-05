from fontmask.rules import RuleSet

rules = RuleSet.load()
assert len(rules.lookups) == 108
assert rules.dot_name == "secret.mask.alnum"
print("fontmask wheel data ok")
