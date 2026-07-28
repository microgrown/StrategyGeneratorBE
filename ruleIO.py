import os
import json
from dataclasses import asdict

from rule import Rule

RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules")


def rulesDir():
    os.makedirs(RULES_DIR, exist_ok=True)
    return RULES_DIR


def rulePath(name):
    return os.path.join(rulesDir(), name + ".json")


def listRuleNames(ruleType=None):
    names = sorted(
        f[:-len(".json")] for f in os.listdir(rulesDir()) if f.endswith(".json")
    )
    if ruleType is None:
        return names
    return [n for n in names if loadRule(n).type == ruleType]


def saveRule(rule):
    with open(rulePath(rule.name), "w") as f:
        json.dump(asdict(rule), f, indent=4)


def loadRule(name):
    with open(rulePath(name)) as f:
        return Rule.from_dict(json.load(f))
