"""Save/load whole-strategy templates: the full main-GUI state (strategy name,
every pane, the rules placed in them, their Flip/Negate modifiers, and the
per-instance parameter overrides). Stored one JSON file per template in
``templates/``, mirroring ``ruleIO``.

A template is a plain snapshot — it does NOT copy the rule definitions
themselves (those live in ``rules/``); it only records which rules are placed
where, so editing a rule later is reflected the next time the template loads.
"""

import os
import json

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def templatesDir():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    return TEMPLATES_DIR


def templatePath(name):
    return os.path.join(templatesDir(), name + ".json")


def listTemplateNames():
    return sorted(
        f[:-len(".json")] for f in os.listdir(templatesDir()) if f.endswith(".json")
    )


def saveTemplate(name, data):
    with open(templatePath(name), "w") as f:
        json.dump(data, f, indent=4)


def loadTemplate(name):
    return loadTemplateFile(templatePath(name))


def loadTemplateFile(path):
    """Load a template from an arbitrary path (makeStrategy.py accepts one)."""
    with open(path) as f:
        return json.load(f)
