"""Clones a template walkforward spec once per generated strategy version.

The engine's spec loader rejects unknown keys outright (`bt/wf/spec.cpp`), so
this writer never invents any: it loads a spec the user already trusts, replaces
only "name" and "strategy", optionally overrides "max_bars_back", and writes the
result. Everything else — symbols, timeframes, wf dates, schedules, criterion,
selection — passes through untouched, which is what makes cloning safe.

"name" is not cosmetic: the engine writes results to `runs/<name>/`
(`bt/wf/pipeline.cpp`), so each version needs its own, and it must be safe as a
directory name. strategyWriter.specStem supplies exactly that.
"""

import os
import json
from dataclasses import dataclass, field

from strategyWriter import GenerationError, registryName, specStem

DEFAULT_SPEC_SUBDIR = "specs/generated"

# bt/wf/spec.h: `int max_bars_back = 50;` when the key is absent.
DEFAULT_MAX_BARS_BACK = 50


@dataclass
class SpecResult:
    paths: list = field(default_factory=list)     # written spec files, version order
    removed: list = field(default_factory=list)   # stale specs pruned from a wider run
    outputDir: str = ""
    maxBarsBack: int = DEFAULT_MAX_BARS_BACK      # the value actually in effect


def loadTemplate(path):
    """Read and sanity-check the template spec. Only the two keys this writer
    rewrites are required — everything else is the engine's business."""
    path = (path or "").strip()
    if not path:
        raise GenerationError("No spec template is configured.")
    if not os.path.isfile(path):
        raise GenerationError(f"Spec template not found:\n{path}")
    try:
        with open(path) as f:
            template = json.load(f)
    except (OSError, ValueError) as exc:
        raise GenerationError(f"Spec template is not readable JSON:\n{path}\n\n{exc}")
    if not isinstance(template, dict):
        raise GenerationError(f"Spec template must be a JSON object:\n{path}")
    missing = [key for key in ("name", "strategy") if key not in template]
    if missing:
        raise GenerationError(
            f"Spec template is missing {' and '.join(missing)}:\n{path}"
        )
    return template


def parseMaxBarsBack(value):
    """The GUI field: blank means "leave the template alone" and yields None."""
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        raise GenerationError(f"Max Bars Back must be a whole number, not '{text}'.")
    if parsed < 0:
        raise GenerationError("Max Bars Back must be zero or greater.")
    return parsed


def effectiveMaxBarsBack(template, override):
    """What the engine will actually use, for the generation summary dialog."""
    if override is not None:
        return override
    value = template.get("max_bars_back", DEFAULT_MAX_BARS_BACK)
    return value if isinstance(value, int) else DEFAULT_MAX_BARS_BACK


def buildSpec(template, name, strategy, override=None):
    """One version's spec. Pure; the template is not mutated. Replacing values in
    a copy preserves the template's key order, so the clone stays diffable
    against it."""
    spec = dict(template)
    spec["name"] = name
    spec["strategy"] = strategy
    if override is not None:
        spec["max_bars_back"] = override
    return spec


def specOutputDir(cfg):
    engineDir = (cfg.get("engineDir") or "").strip()
    if not engineDir:
        raise GenerationError("No BacktestEngine root is configured.")
    subdir = cfg.get("specOutputSubdir") or DEFAULT_SPEC_SUBDIR
    return os.path.normpath(os.path.join(engineDir, subdir))


def _pruneStaleSpecs(outputDir, strategyName, versionCount):
    """Remove this strategy's specs above the current version count. Without it a
    run that shrinks from 3 versions to 1 leaves momentum_clone_v2.json behind,
    naming a strategy the registry no longer has — bt_walkforward would fail on
    it. Only this strategy's own stems are touched."""
    removed = []
    version = versionCount + 1
    while True:
        path = os.path.join(outputDir, specStem(strategyName, version) + ".json")
        if not os.path.exists(path):
            break
        os.remove(path)
        removed.append(path)
        version += 1
    return removed


def writeSpecs(strategyName, versionCount, cfg):
    """Write one spec per version beside the engine's own specs. Version numbers
    and registry names come from strategyWriter, so the spec's "strategy" value
    always matches what was registered."""
    template = loadTemplate(cfg.get("specTemplate"))
    override = parseMaxBarsBack(cfg.get("maxBarsBack"))
    outputDir = specOutputDir(cfg)

    os.makedirs(outputDir, exist_ok=True)
    paths = []
    for version in range(1, versionCount + 1):
        stem = specStem(strategyName, version)
        spec = buildSpec(
            template, stem, registryName(strategyName, version), override
        )
        path = os.path.join(outputDir, stem + ".json")
        with open(path, "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")
        paths.append(path)

    return SpecResult(
        paths=paths,
        removed=_pruneStaleSpecs(outputDir, strategyName, versionCount),
        outputDir=outputDir,
        maxBarsBack=effectiveMaxBarsBack(template, override),
    )
