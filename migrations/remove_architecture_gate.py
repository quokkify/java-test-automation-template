"""Copier migration to 2.0.0: remove the q4j architecture gate that the ArchGate plugin replaces.

Runs in the root of the updated project. It only removes what belonged to the old gate, so the build works
again; adopting the ArchGate plugin is section 3 of docs/agents/architecture-verification.md. Every step is
idempotent: a second run, or a run on a project that never had the gate, changes nothing.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

GATE_SCRIPT = Path("gradle/architecture.gradle")
GATE_TOOLS = Path("tools/architecture")
BUILD_FILES = (Path("build.gradle"), Path("build.gradle.kts"))
CATALOG = Path("gradle/libs.versions.toml")
PROPERTIES = Path("gradle.properties")
APPLY_LINE = re.compile(r"""^[ \t]*apply[ \t(]+from[ \t:=]+["']gradle/architecture\.gradle["'][ \t)]*;?[ \t]*\r?\n?""",
                        re.M)
GATE_PROPERTY = re.compile(r"^[ \t]*architecture\.(packages|fail\.on)[ \t]*[=:].*\r?\n?", re.M)
# Catalog aliases that only the old runner used, and the accessor that a build script would use for each.
RUNNER_LIBRARIES = {
    "q4j-architecture": "libs.q4j.architecture",
    "log4j-core": "libs.log4j.core",
    "log4j-slf4j2-impl": "libs.log4j.slf4j2.impl",
}


def build_scripts(root: Path) -> list[Path]:
    """Every Gradle script of the project outside build output and caches."""
    skipped = {"build", ".gradle", ".git"}
    return [path for pattern in ("*.gradle", "*.gradle.kts") for path in root.rglob(pattern)
            if not skipped.intersection(path.relative_to(root).parts)]


def drop_apply_line() -> None:
    for build in BUILD_FILES:
        if build.is_file():
            text = build.read_text()
            updated = APPLY_LINE.sub("", text)
            if updated != text:
                build.write_text(updated)
                print(f"removed the gradle/architecture.gradle apply line from {build}")


def drop_gate_files() -> None:
    if GATE_SCRIPT.is_file():
        GATE_SCRIPT.unlink()
        print(f"removed {GATE_SCRIPT}")
    if GATE_TOOLS.is_dir():
        shutil.rmtree(GATE_TOOLS)
        print(f"removed {GATE_TOOLS}/")
        tools = GATE_TOOLS.parent
        if tools.is_dir() and not any(tools.iterdir()):
            tools.rmdir()


def drop_catalog_entries() -> None:
    """Remove the runner libraries that no build script uses, then the log4j version if nothing refers to it."""
    if not CATALOG.is_file():
        return
    scripts = "\n".join(path.read_text() for path in build_scripts(Path(".")))
    text = CATALOG.read_text()
    for alias, accessor in RUNNER_LIBRARIES.items():
        if re.search(re.escape(accessor) + r"\b", scripts):
            print(f"kept {alias} in {CATALOG}: a build script uses {accessor}")
            continue
        text = re.sub(rf"^[ \t]*{re.escape(alias)}[ \t]*=.*\r?\n?", "", text, flags=re.M)
    if not re.search(r"""version\.ref[ \t]*=[ \t]*["']log4j["']""", text) and "libs.versions.log4j" not in scripts:
        text = re.sub(r"^[ \t]*log4j[ \t]*=.*\r?\n?", "", text, flags=re.M)
    if text != CATALOG.read_text():
        CATALOG.write_text(text)
        print(f"removed the architecture runner entries from {CATALOG}")


def drop_gate_properties() -> None:
    if not PROPERTIES.is_file():
        return
    text = PROPERTIES.read_text()
    updated = GATE_PROPERTY.sub("", text)
    if updated == text:
        return
    if updated.strip():
        PROPERTIES.write_text(updated)
        print(f"removed the architecture.* properties from {PROPERTIES}")
    else:
        PROPERTIES.unlink()
        print(f"removed {PROPERTIES}: it held only architecture.* properties")


def main() -> None:
    drop_apply_line()
    drop_gate_files()
    drop_catalog_entries()
    drop_gate_properties()
    print("The q4j architecture gate is removed. To enable the ArchGate plugin that replaces it, follow section 3 "
          "of docs/agents/architecture-verification.md, and replace verifyArchitecture with archgateCheck in CI.")


if __name__ == "__main__":
    main()
