"""Copier migration to 2.0.0: remove the q4j architecture gate that the ArchGate plugin replaces.

Runs in the root of the updated project. It only removes what belonged to the old gate, so the build works
again; adopting the ArchGate plugin is section 3 of docs/agents/architecture-verification.md. Every step is
idempotent: a second run, or a run on a project that never had the gate, changes nothing.

All files are read before anything is written, as bytes decoded with surrogateescape: no file can fail to
decode halfway through, and bytes and line endings that are written back stay as they were.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

GATE_SCRIPT = Path("gradle/architecture.gradle")
GATE_TOOLS = Path("tools/architecture")
GATE_REGISTRY = GATE_TOOLS / "META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule"
DEFAULT_RULES = {
    f"dev.quokkify.architecture.rules.{name}"
    for name in ("JavaConventionsRule", "NoConsoleOutputRule", "NoDeprecatedApiRule", "ServiceRegistrationRule",
                 "TestClassNamingRule")
}
CATALOG = Path("gradle/libs.versions.toml")
PROPERTIES = Path("gradle.properties")
SPEC = "section 3 of docs/agents/architecture-verification.md"
# apply from: 'gradle/architecture.gradle', file('...'), rootProject.file('...'), "$rootDir/...", "${rootDir}/...",
# and the Kotlin DSL apply(from = "...").
APPLY_LINE = re.compile(
    r"""^[ \t]*apply[ \t]*\(?[ \t]*from[ \t]*[:=][ \t]*(?:(?:rootProject\.)?file[ \t]*\([ \t]*)?"""
    r"""["'](?:\$\{?rootDir\}?/)?gradle/architecture\.gradle["'][ \t]*\)?[ \t]*\)?[ \t]*;?[ \t]*(?:\r\n|\n|$)""",
    re.M)
GATE_PROPERTY = re.compile(r"^[ \t]*architecture\.(?:packages|fail\.on)[ \t]*[=:].*(?:\r\n|\n|$)", re.M)
RUNNER_LIBRARIES = ("q4j-architecture", "log4j-core", "log4j-slf4j2-impl")
RUNNER_VERSION = "log4j"


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "surrogateescape")


def write(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8", "surrogateescape"))


def build_scripts() -> list[Path]:
    """Every Gradle script of the project outside build output and caches."""
    skipped = {"build", ".gradle", ".git"}
    return sorted(path for pattern in ("*.gradle", "*.gradle.kts") for path in Path(".").rglob(pattern)
                  if not skipped.intersection(path.parts))


def alias_pattern(alias: str) -> str:
    """Gradle treats '-', '_' and '.' in an alias the same way."""
    return r"[-_.]".join(re.escape(part) for part in re.split(r"[-_.]", alias))


def lines_matching(scripts: dict[Path, str], pattern: str) -> list[str]:
    return [f"{path}:{number}: {line.strip()}"
            for path, text in scripts.items()
            for number, line in enumerate(text.splitlines(), 1)
            if re.search(pattern, line)]


def library_used(alias: str, scripts: str, catalog: str) -> bool:
    name = alias_pattern(alias)
    in_scripts = rf"""\blibs\.{name}\b|findLibrary\(\s*["']{name}["']"""
    bundles = catalog.split("[bundles]", 1)[1] if "[bundles]" in catalog else ""
    bundles = re.split(r"^\s*\[", bundles, maxsplit=1, flags=re.M)[0]
    return bool(re.search(in_scripts, scripts) or re.search(rf"""["']{name}["']""", bundles))


def version_used(version: str, scripts: str, catalog: str) -> bool:
    name = alias_pattern(version)
    return bool(re.search(rf"""\bref\s*=\s*["']{name}["']""", catalog)
                or re.search(rf"""\blibs\.versions\.{name}\b|findVersion\(\s*["']{name}["']""", scripts))


def main() -> None:
    # Read everything first.
    scripts = {path: read(path) for path in build_scripts() if path != GATE_SCRIPT}
    catalog = read(CATALOG) if CATALOG.is_file() else None
    properties = read(PROPERTIES) if PROPERTIES.is_file() else None
    registry = read(GATE_REGISTRY) if GATE_REGISTRY.is_file() else ""

    # Plan every change in memory.
    writes: dict[Path, str] = {}
    for path, text in scripts.items():
        updated = APPLY_LINE.sub("", text)
        if updated != text:
            writes[path] = updated
            print(f"removed the gradle/architecture.gradle apply line from {path}")
    remaining = {path: writes.get(path, text) for path, text in scripts.items()}
    joined = "\n".join(remaining.values())

    still_applied = lines_matching(remaining, r"architecture\.gradle")
    leftover_tasks = lines_matching(remaining, r"\bverifyArchitecture\b")

    if catalog is not None:
        text = catalog
        for alias in RUNNER_LIBRARIES:
            if library_used(alias, joined, text):
                print(f"kept {alias} in {CATALOG}: the build still uses it")
                continue
            text = re.sub(rf"^[ \t]*{re.escape(alias)}[ \t]*=.*(?:\r\n|\n|$)", "", text, flags=re.M)
        if version_used(RUNNER_VERSION, joined, text):
            print(f"kept the {RUNNER_VERSION} version in {CATALOG}: the build still uses it")
        else:
            text = re.sub(rf"^[ \t]*{RUNNER_VERSION}[ \t]*=.*(?:\r\n|\n|$)", "", text, flags=re.M)
        if text != catalog:
            writes[CATALOG] = text
            print(f"removed the architecture runner entries from {CATALOG}")

    delete_properties = False
    if properties is not None:
        updated = GATE_PROPERTY.sub("", properties)
        if updated != properties:
            if updated.strip():
                writes[PROPERTIES] = updated
                print(f"removed the architecture.* properties from {PROPERTIES}")
            else:
                delete_properties = True

    custom_rules = [line.strip() for line in registry.splitlines()
                    if line.strip() and not line.strip().startswith("#") and line.strip() not in DEFAULT_RULES]

    had_gate = bool(writes or delete_properties or GATE_SCRIPT.is_file() or GATE_TOOLS.is_dir())

    # Apply the plan.
    for path, text in writes.items():
        write(path, text)
    if delete_properties:
        PROPERTIES.unlink()
        print(f"removed {PROPERTIES}: it held only architecture.* properties")
    if GATE_SCRIPT.is_file():
        if still_applied:
            print(f"WARNING: kept {GATE_SCRIPT}, because a build script still refers to it; remove these lines "
                  "by hand, then the file:")
            for line in still_applied:
                print(f"  {line}")
        else:
            GATE_SCRIPT.unlink()
            print(f"removed {GATE_SCRIPT}")
    if custom_rules:
        print(f"WARNING: {GATE_REGISTRY} listed rules that the template did not; port them to ArchGate rules "
              f"({SPEC}, step 6):")
        for rule in custom_rules:
            print(f"  {rule}")
    if GATE_TOOLS.is_dir():
        shutil.rmtree(GATE_TOOLS)
        print(f"removed {GATE_TOOLS}/")
        if GATE_TOOLS.parent.is_dir() and not any(GATE_TOOLS.parent.iterdir()):
            GATE_TOOLS.parent.rmdir()
    if leftover_tasks:
        print("WARNING: these lines still name the removed verifyArchitecture task; use archgateCheck instead:")
        for line in leftover_tasks:
            print(f"  {line}")

    if not had_gate:
        return
    banner = "=" * 78
    print(f"\n{banner}\nWARNING: THE ARCHITECTURE GATE IS NOW DISABLED in this project.\n"
          f"The q4j gate is removed, and the ArchGate plugin that replaces it is not applied yet.\n"
          f"Follow {SPEC} to enable it, and replace verifyArchitecture with archgateCheck in CI.\n{banner}")


if __name__ == "__main__":
    main()
