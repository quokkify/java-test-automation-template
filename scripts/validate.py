#!/usr/bin/env python3
"""Render the Java test automation template, check update ownership, and optionally compile it."""

from __future__ import annotations

import argparse
import shutil
import re
import subprocess
import tempfile
from pathlib import Path

import yaml
from copier import run_copy, run_update

ROOT = Path(__file__).resolve().parents[1]
GRADLE_TASKS = [
    "assemble", "testClasses", "checkstyleMain", "checkstyleTest",
    "spotbugsMain", "spotbugsTest", "verifyArchitecture",
]
EXPECTED = [
    ".copier-answers.yml", ".gitattributes", ".gitignore", "README.md", "AGENTS.md",
    "build.gradle", "settings.gradle", "gradle.properties", "gradlew", "gradlew.bat",
    "gradle/wrapper/gradle-wrapper.jar", "gradle/wrapper/gradle-wrapper.properties",
    "gradle/libs.versions.toml", "gradle/code-analysis.gradle",
    "gradle/compilation.gradle", "gradle/dependencies.gradle", "gradle/tests.gradle",
    "gradle/architecture.gradle", "docs/agents/architecture-verification.md",
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
    "tools/architecture/log4j2.xml",
    "tools/architecture/META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule",
    "src/test/resources/META-INF/services/org.testng.ITestNGListener", "docs/agents/test-execution.md",
]
MANAGED = {"README.md", "AGENTS.md", "docs/agents/architecture-verification.md", "docs/agents/test-execution.md",
           ".copier-answers.yml"}


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


ADOPTION = [
    "src/test/resources/META-INF/services/org.testng.ITestNGListener", "docs/agents/test-execution.md",
    "gradle.properties", "gradle/architecture.gradle", "docs/agents/architecture-verification.md",
    "tools/architecture/log4j2.xml",
    "tools/architecture/META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule",
]


def validate_gate_adoption(temporary: Path) -> None:
    """A project generated before the architecture gate gets its files on update, never its build edits."""
    source = temporary / "legacy-source"
    source.mkdir()
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    for name in ADOPTION:
        template_name = name + ".jinja" if name == "gradle.properties" else name
        (source / "template" / template_name).unlink()
    init_git(source)
    commit(source, "Template before the architecture gate")
    run(["git", "tag", "v1.0.0"], source)

    project = temporary / "legacy-project"
    run_copy(str(source), project, defaults=True, vcs_ref="v1.0.0")
    init_git(project)
    build = b"project-owned build without the gate\n"
    (project / "build.gradle").write_bytes(build)
    commit(project, "Legacy project")

    shutil.rmtree(source / "template")
    shutil.copytree(ROOT / "template", source / "template")
    commit(source, "Template with the architecture gate")
    run(["git", "tag", "v2.0.0"], source)

    run_update(project, defaults=True, overwrite=True, vcs_ref="v2.0.0")
    for name in ADOPTION:
        assert (project / name).is_file(), f"update must add the missing {name}"
    assert (project / "build.gradle").read_bytes() == build, "update must leave build.gradle to the project"


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
        properties = (project / "gradle.properties").read_text()
        assert properties.strip() == "architecture.packages=com.example.test_automation", properties
        assert "apply from: 'gradle/architecture.gradle'" in (project / "build.gradle").read_text()
        catalog = (project / "gradle/libs.versions.toml").read_text()
        q4j = tuple(int(part) for part in re.search(r'^q4j = "([0-9.]+)"', catalog, re.M).group(1).split("."))
        assert q4j >= (0, 9, 0), f"architecture needs q4j 0.9.0 or later, got {q4j}"
        for alias in ("q4j-architecture", "log4j-core", "log4j-slf4j2-impl"):
            assert re.search(rf"^{alias} = ", catalog, re.M), f"catalog must declare {alias}"
        registry = project / "tools/architecture/META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule"
        registered = {line.strip().rsplit(".", 1)[-1] for line in registry.read_text().splitlines()
                      if line.strip() and not line.startswith("#")}
        spec = (project / "docs/agents/architecture-verification.md").read_text()
        documented = set(re.findall(r"^\| `(\w+Rule)` ", spec, re.M))
        assert registered == documented, f"registered {registered} but the spec documents {documented}"
        listeners = (project / "src/test/resources/META-INF/services/org.testng.ITestNGListener").read_text().split()
        for listener in ("dev.quokkify.listener.lifecycle.SuiteListener", "dev.quokkify.listener.retry.RetryListener"):
            assert listener in listeners, f"{listener} must be registered"
        assert re.search(r"^q4j-testng = ", catalog, re.M), "catalog must declare q4j-testng"
        assert "implementation libs.q4j.testng" in (project / "gradle/dependencies.gradle").read_text()
        for gradle_file in (project / "gradle").glob("*.gradle"):
            assert not re.search(r"includeGroups|excludeGroups", gradle_file.read_text()), gradle_file
        for java_file in (project / "src").rglob("*.java"):
            assert not re.search(r"groups *=", java_file.read_text()), f"{java_file} selects tests by TestNG group"
        for guide in ("AGENTS.md", "README.md"):
            text = (project / guide).read_text()
            assert "](docs/agents/test-execution.md)" in text, guide
            assert "](docs/agents/architecture-verification.md)" in text, guide
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
        assert "architecture.packages=dev.quokkify.marketdesk" in (custom / "gradle.properties").read_text()
        # Checkstyle's CustomImportOrder puts dev.quokkify in its own group and sorts other third-party
        # imports together, so the starter imports depend on the base package.
        late = temporary / "late"
        run_copy(str(source), late, data={"package_root": "org.zeta", "package_name": "suite"},
                 defaults=True, vcs_ref="HEAD")
        imports = {
            custom / "src/test/java/dev/quokkify/marketdesk/test/StarterTest.java":
                "import dev.quokkify.marketdesk.config.StarterConfig;\n\nimport org.testng.annotations.Test;\n",
            late / "src/test/java/org/zeta/suite/test/StarterTest.java":
                "import org.testng.annotations.Test;\nimport org.zeta.suite.config.StarterConfig;\n",
            project / "src/test/java/com/example/test_automation/test/StarterTest.java":
                "import com.example.test_automation.config.StarterConfig;\nimport org.testng.annotations.Test;\n",
        }
        for starter_test, expected in imports.items():
            assert expected in starter_test.read_text(), f"{starter_test} imports break CustomImportOrder"
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
            tested = subprocess.run(["./gradlew", "--no-daemon", "--console=plain", "test", "--rerun"], cwd=project,
                                    check=True, capture_output=True, text=True).stdout
            assert "> Concurrency > " in tested, "SuiteListener must run the tests in its parallel block"
            planned = subprocess.run(["./gradlew", "--no-daemon", "-q", "check", "--dry-run"], cwd=project,
                                     check=True, capture_output=True, text=True).stdout
            assert ":verifyArchitecture" in planned, "check must run verifyArchitecture"
            for variant in (custom, late):
                run(["./gradlew", "--no-daemon", "checkstyleMain", "checkstyleTest"], variant)

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
        validate_gate_adoption(temporary)
    print("java-test-automation-template validation: OK" + (" (static)" if static else " (with Gradle)"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="skip the Gradle build")
    validate(parser.parse_args().static)
