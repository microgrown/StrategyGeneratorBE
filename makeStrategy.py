"""Headless Make Strategy: generate a strategy from a saved template, no GUI.

    python makeStrategy.py "<template name or path>" [options]

Does exactly what the main window's Make Strategy button does -- writes the
generated header, refreshes the registry .inc files and manifest, clones one
walkforward spec per version, and re-saves the template under the strategy
name -- but driven from a template JSON in ``templates/`` instead of the pane
widgets. Pair it with runBatch.py for a fully scripted loop:

    python makeStrategy.py "202608 BAS-12"
    .\\scripts\\build.ps1 -Config Release        (in the engine repo)
    python runBatch.py s_202608_bas_12 --prune

Options override the template / config.json for this invocation only
(config.json is never written):

    --name NAME             strategy name (default: the template's strategyName)
    --max-bars-back N       Max Bars Back (default: the template's, else config)
    --engine-dir DIR        BacktestEngine root (default: config.json)
    --spec-template PATH    spec JSON to clone per version (default: config.json)
    --no-save-template      do not write templates/<name>.json afterwards

Exit code 0 on success, 1 on any error (one line on stderr).
"""

import argparse
import os
import sys

import config
import specWriter
import strategyWriter
import templateIO
from strategyWriter import GenerationError

# The pane / item shapes strategyWriter consumes. mainGUI.RulePane and
# mainGUI.RuleItem are the widget-backed originals; these carry the same
# fields without tkinter, built straight from templateIO's JSON snapshot
# (mainGUI._serializeState writes that format; this is its reader).


class TemplateItem:
    def __init__(self, name, flipped=False, negated=False, params=None):
        self.name = name
        self.flipped = flipped
        self.negated = negated
        self.params = params if params is not None else {}


class TemplatePane:
    def __init__(self, ruleType, items):
        self.ruleType = ruleType
        self.items = items


def panesFromTemplate(data):
    """Template JSON -> [TemplatePane]. Delimiters stay as their string form,
    which is what strategyWriter._templateGroups splits on."""
    panes = []
    for paneData in data.get("panes", []):
        items = []
        for raw in paneData.get("items", []):
            if isinstance(raw, str):
                items.append(raw)
            else:
                items.append(TemplateItem(
                    raw.get("name", ""),
                    flipped=raw.get("flipped", False),
                    negated=raw.get("negated", False),
                    params=raw.get("params", {}),
                ))
        panes.append(TemplatePane(paneData.get("ruleType", "Entry"), items))
    return panes


def resolveTemplate(spec):
    """A bare name looks in templates/; an existing .json path is loaded
    directly. Returns the template data."""
    spec = (spec or "").strip()
    if not spec:
        raise GenerationError("Template name is required.")
    if spec.lower().endswith(".json") and os.path.isfile(spec):
        return templateIO.loadTemplateFile(spec)
    if spec not in templateIO.listTemplateNames():
        raise GenerationError(
            f"No template named '{spec}' in {templateIO.templatesDir()}."
        )
    return templateIO.loadTemplate(spec)


def effectiveConfig(cfg, data, engineDir=None, specTemplate=None, maxBarsBack=None):
    """config.json plus the template's own Max Bars Back plus per-invocation
    overrides, highest precedence last. Pure: nothing is written back."""
    cfg = dict(cfg)
    templateMbb = (data.get("maxBarsBack") or "").strip()
    if templateMbb:
        cfg["maxBarsBack"] = templateMbb
    if engineDir is not None:
        cfg["engineDir"] = engineDir
    if specTemplate is not None:
        cfg["specTemplate"] = specTemplate
    if maxBarsBack is not None:
        cfg["maxBarsBack"] = maxBarsBack
    return cfg


def makeStrategy(data, cfg, name=None, saveTemplate=True):
    """The GUI's _makeStrategy without the dialogs. `data` is a template snapshot
    (templateIO format); `cfg` is the fully resolved config (effectiveConfig).
    Returns (strategyName, GenerationResult, SpecResult). Raises GenerationError."""
    # Late import: mainGUI pulls in tkinter; only its pure helpers are needed.
    from mainGUI import engineDirProblem

    strategyName = (name or data.get("strategyName") or "").strip()
    if not strategyName:
        raise GenerationError("Strategy name is required (template has none; pass --name).")
    problem = engineDirProblem(cfg.get("engineDir"))
    if problem:
        raise GenerationError(problem)

    panes = panesFromTemplate(data)
    if not panes:
        raise GenerationError("The template has no rule panes.")

    # Same order as the GUI: validate spec inputs BEFORE generate() writes the
    # header, so a bad spec template cannot leave a header with no specs.
    specWriter.loadTemplate(cfg.get("specTemplate"))
    specWriter.parseMaxBarsBack(cfg.get("maxBarsBack"))
    result = strategyWriter.generate(strategyName, panes, cfg)
    specResult = specWriter.writeSpecs(strategyName, result.versionCount, cfg)

    if saveTemplate:
        snapshot = dict(data)
        snapshot["strategyName"] = strategyName
        snapshot["maxBarsBack"] = str(cfg.get("maxBarsBack") or "")
        templateIO.saveTemplate(strategyName, snapshot)

    return strategyName, result, specResult


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a BacktestEngine strategy from a saved template (no GUI).")
    parser.add_argument("template",
                        help="template name in templates/, or a path to a template .json")
    parser.add_argument("--name", help="strategy name (default: the template's)")
    parser.add_argument("--max-bars-back", dest="maxBarsBack",
                        help="Max Bars Back override (default: template, then config.json)")
    parser.add_argument("--engine-dir", dest="engineDir",
                        help="BacktestEngine root (default: config.json)")
    parser.add_argument("--spec-template", dest="specTemplate",
                        help="walkforward spec to clone per version (default: config.json)")
    parser.add_argument("--no-save-template", dest="saveTemplate", action="store_false",
                        help="do not re-save the template under the strategy name")
    args = parser.parse_args(argv)

    try:
        data = resolveTemplate(args.template)
        cfg = effectiveConfig(config.load(), data, engineDir=args.engineDir,
                              specTemplate=args.specTemplate, maxBarsBack=args.maxBarsBack)
        name, result, specResult = makeStrategy(data, cfg, name=args.name,
                                                saveTemplate=args.saveTemplate)
    except GenerationError as exc:
        print(f"makeStrategy: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # still one line on stderr, not a traceback
        print(f"makeStrategy: failed to generate strategy: {exc}", file=sys.stderr)
        return 1

    from mainGUI import summaryText
    print(summaryText(name, result, specResult))
    return 0


if __name__ == "__main__":
    sys.exit(main())
