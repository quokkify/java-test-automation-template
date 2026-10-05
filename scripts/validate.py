#!/usr/bin/env python3
"""Render the Java test automation template, check update ownership, and optionally compile it."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml
from copier import run_copy, run_update

ROOT = Path(__file__).resolve().parents[1]
GRADLE_TASKS = [
    "assemble", "testClasses", "checkstyleMain", "checkstyleTest",
    "spotbugsMain", "spotbugsTest",
]
EXPECTED = [
    ".copier-answers.yml", ".gitattributes", ".gitignore", "README.md", "AGENTS.md",
    "build.gradle", "settings.gradle", "gradlew", "gradlew.bat",
    "gradle/wrapper/gradle-wrapper.jar", "gradle/wrapper/gradle-wrapper.properties",
    "gradle/libs.versions.toml", "gradle/code-analysis.gradle",
    "gradle/compilation.gradle", "gradle/dependencies.gradle", "gradle/tests.gradle",
    "src/main/resources/starter.properties",
    *(f"src/main/java/com/example/test_automation/{name}" for name in (
        "config/package-info.java", "config/StarterConfig.java", "config/StarterConfiguration.java",
        "model/package-info.java", "service/package-info.java", "helper/package-info.java",
        "verification/package-info.java", "step/package-info.java", "step/BaseSteps.java",
    )),
    *(f"src/test/java/com/example/test_automation/test/{name}" for name in (
        "package-info.java", "BaseTest.java", "StarterTest.java",
    )),
    "tools/checkstyle/checkstyle.xml", "tools/spotbugs/excludeFilter.xml",
]
MANAGED = {"README.md", "AGENTS.md", ".copier-answers.yml"}


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def init_git(directory: Path) -> None:
    run(["git", "init", "-q", "-b", "main"], directory)
    for key, value in (
        ("user.name", "Fixture"),
        ("user.email", "fixture@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ):
        run(["git", "config", key, value], directory)


def commit(directory: Path, message: str) -> None:
    run(["git", "add", "-A"], directory)
    run(["git", "commit", "--no-verify", "-qm", message], directory)


def snapshot(directory: Path) -> dict[Path, bytes]:
    return {
        p.relative_to(directory): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(directory).parts
    }


def validate(static: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="java-test-automation-template-") as tmp:
        temporary = Path(tmp).resolve()
        source = temporary / "source"
        source.mkdir()
        shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
        shutil.copytree(ROOT / "template", source / "template")
        init_git(source)
        commit(source, "Current working template")

        project = temporary / "test-automation"
        run_copy(str(source), project, defaults=True, vcs_ref="HEAD")

        for name in EXPECTED:
            assert (project / name).is_file(), f"missing generated file: {name}"
        assert (project / "gradlew").stat().st_mode & 0o111, "wrapper must be executable"
        for path in project.rglob("*"):
            if path.is_file() and path.suffix not in {".jar"} and path.name != "gradlew.bat":
                text = path.read_text()
                assert "{%" not in text, f"unrendered block tag in {path.name}"
                assert "{{" not in text, f"unrendered expression in {path.name}"
        settings = (project / "settings.gradle").read_text()
        assert settings.strip() == 'rootProject.name = "test-automation"', settings
        answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
        assert answers["project_name"] == "test-automation", answers
        assert answers["_src_path"], "answers must record the template source"
        assert answers["package_root"] == "com.example", answers
        assert answers["package_name"] == "test_automation", answers
        starter = project / "src/test/java/com/example/test_automation/test/StarterTest.java"
        assert starter.read_text().startswith("package com.example.test_automation.test;"), starter

        named = temporary / "named"
        run_copy(str(source), named, data={"project_name": "qa.suite"}, defaults=True, vcs_ref="HEAD")
        assert 'rootProject.name = "qa.suite"' in (named / "settings.gradle").read_text()
        assert (named / "src/main/java/com/example/qa_suite/step/BaseSteps.java").is_file()
        digits = temporary / "digits"
        run_copy(str(source), digits, data={"project_name": "123-app"}, defaults=True, vcs_ref="HEAD")
        assert (digits / "src/main/java/com/example/p_123_app/step/BaseSteps.java").is_file()
        custom = temporary / "custom"
        run_copy(str(source), custom, data={"package_root": "dev.quokkify", "package_name": "marketdesk"},
                 defaults=True, vcs_ref="HEAD")
        base_steps = custom / "src/main/java/dev/quokkify/marketdesk/step/BaseSteps.java"
        assert base_steps.read_text().startswith("package dev.quokkify.marketdesk.step;"), base_steps
        for index, bad in enumerate((
            {"project_name": "-bad name"},
            {"package_root": "Dev.Quokkify"},
            {"package_root": "dev..quokkify"},
            {"package_name": "market.desk"},
            {"package_name": "1desk"},
            {"package_name": "class"},
            {"package_root": "com.new"},
        )):
            try:
                run_copy(str(source), temporary / f"bad{index}", data=bad, defaults=True, vcs_ref="HEAD")
            except Exception:
                pass
            else:
                raise AssertionError(f"invalid answer accepted: {bad}")

        if not static:
            run(["./gradlew", "--no-daemon", *GRADLE_TASKS], project)

        shutil.rmtree(project / ".gradle", ignore_errors=True)
        shutil.rmtree(project / "build", ignore_errors=True)
        init_git(project)
        markers: dict[str, bytes] = {}
        for name in EXPECTED:
            if name in MANAGED:
                continue
            marker = b"project-owned fixture content\n"
            (project / name).write_bytes(marker)
            markers[name] = marker
        commit(project, "Project customization")

        template = source / "template"
        for path in template.rglob("*"):
            if path.is_file():
                with path.open("ab") as stream:
                    stream.write(b"Updated template fixture content\n")
        (template / "added-by-update.txt").write_text("new\n")
        commit(source, "Updated template")
        run(["git", "tag", "v9.9.9"], source)

        run_update(project, defaults=True, overwrite=True, vcs_ref="v9.9.9")
        for name, marker in markers.items():
            assert (project / name).read_bytes() == marker, f"update replaced {name}"
        for name in MANAGED - {".copier-answers.yml"}:
            assert "Updated template fixture content" in (project / name).read_text(), (
                f"{name} must be refreshed by update"
            )
        assert (project / "added-by-update.txt").is_file(), "new template files must be added"
    print("java-test-automation-template validation: OK" + (" (static)" if static else " (with Gradle)"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="skip the Gradle build")
    validate(parser.parse_args().static)
