#!/usr/bin/env python3
"""Render the Java test automation template, check update ownership, and optionally compile it."""

from __future__ import annotations

import argparse
import json
import shutil
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from copier import run_copy, run_update
from copier.errors import UnsafeTemplateError

ROOT = Path(__file__).resolve().parents[1]
RULE_REGISTRY = "src/test/resources/META-INF/services/dev.quokkify.archgate.api.ArchitectureRule"
GRADLE_TASKS = [
    "assemble", "testClasses", "checkstyleMain", "checkstyleTest",
    "spotbugsMain", "spotbugsTest", "archgateCheck",
]
EXPECTED = [
    ".copier-answers.yml", ".gitattributes", ".gitignore", "README.md", "AGENTS.md",
    "build.gradle", "settings.gradle", "gradlew", "gradlew.bat",
    "gradle/wrapper/gradle-wrapper.jar", "gradle/wrapper/gradle-wrapper.properties",
    "gradle/libs.versions.toml", "gradle/code-analysis.gradle",
    "gradle/compilation.gradle", "gradle/dependencies.gradle", "gradle/tests.gradle",
    "docs/agents/architecture-verification.md",
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
    "src/test/resources/META-INF/services/dev.quokkify.archgate.api.ArchitectureRule",
    "src/test/resources/META-INF/services/org.testng.ITestNGListener", "docs/agents/test-execution.md",
    "gradle/allure.gradle", "docs/agents/test-reporting.md",
]
MANAGED = {"README.md", "AGENTS.md", "docs/agents/architecture-verification.md", "docs/agents/test-execution.md",
           "docs/agents/test-reporting.md", ".copier-answers.yml"}
SEED_MAIN = "seed/src/main/java/com/example/test_automation/seed"
SEED_TEST = "seed/src/test/java/com/example/test_automation/seed"
SEED_PACKAGES = ("scenario", "generate", "format", "files", "stand", "load", "checkpoint", "cli")
SEED_EXPECTED = [
    "seed/build.gradle", "seed/gradle/dependencies.gradle", "seed/gradle/seed.versions.toml",
    "docs/agents/seed-module.md", "src/main/resources/seed.properties",
    "src/main/java/com/example/test_automation/config/SeedConfig.java",
    "src/main/java/com/example/test_automation/config/SeedConfiguration.java",
    *(f"{SEED_MAIN}/{package}/package-info.java" for package in SEED_PACKAGES),
    *(f"{SEED_MAIN}/{name}" for name in (
        "scenario/Scenario.java", "scenario/SyntheticUser.java", "scenario/SyntheticMarkers.java",
        "scenario/SeedJson.java", "generate/SizePreset.java", "generate/FakeValues.java",
        "generate/ScenarioGenerator.java", "format/UserCsv.java", "files/PngFixture.java", "stand/StandProbe.java",
        "load/ScenarioLoader.java", "checkpoint/Checkpoint.java", "checkpoint/CheckpointDiff.java",
        "cli/SeedCli.java", "cli/GenerateCommand.java", "cli/LoadCommand.java", "cli/DiffCommand.java",
    )),
    f"{SEED_TEST}/cli/SeedCliTest.java", "seed/src/test/resources/golden/scenario-seed-1-small.json",
    "seed/src/test/resources/META-INF/services/dev.quokkify.archgate.api.ArchitectureRule",
    "seed/src/test/resources/META-INF/services/org.testng.ITestNGListener",
]
SEED_MANAGED = {"seed/build.gradle", "docs/agents/seed-module.md"}


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


# The q4j architecture gate of templates before 2.0.0, reduced to what the 2.0.0 migration must remove.
LEGACY_GATE = {
    "gradle/architecture.gradle": "tasks.register('verifyArchitecture')\n",
    "tools/architecture/log4j2.xml": "<Configuration/>\n",
    "tools/architecture/META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule":
        "dev.quokkify.architecture.rules.NoConsoleOutputRule\n",
    "gradle.properties.jinja": "architecture.packages={{ base_package }}\n",
}
LEGACY_CATALOG = {
    "[versions]\n": '[versions]\nlog4j = "2.26.1"\n',
    "[libraries]\n": (
        '[libraries]\nq4j-architecture = { module = "dev.quokkify:architecture", version.ref = "q4j" }\n'
        'log4j-core = { module = "org.apache.logging.log4j:log4j-core", version.ref = "log4j" }\n'
        'log4j-slf4j2-impl = { module = "org.apache.logging.log4j:log4j-slf4j2-impl", version.ref = "log4j" }\n'
    ),
}
GATE_LEFTOVERS = ("gradle/architecture.gradle", "tools/architecture", "gradle.properties")


def legacy_template(template: Path) -> None:
    """Turn a copy of the current template into one with the q4j gate instead of the ArchGate plugin."""
    build = template / "build.gradle.jinja"
    text = build.read_text()
    text = text.replace("    alias(libs.plugins.archgate)\n", "")
    text = text[:text.index("\n// ArchGate")] + "\napply from: 'gradle/architecture.gradle'\n"
    build.write_text(text)
    catalog = template / "gradle/libs.versions.toml"
    lines = [line for line in catalog.read_text().splitlines(keepends=True) if "archgate" not in line]
    text = "".join(lines)
    for anchor, replacement in LEGACY_CATALOG.items():
        text = text.replace(anchor, replacement)
    catalog.write_text(text)
    dependencies = template / "gradle/dependencies.gradle"
    dependencies.write_text("".join(line for line in dependencies.read_text().splitlines(keepends=True)
                                    if "archgate" not in line))
    (template / RULE_REGISTRY).unlink()
    (template / "docs/agents/architecture-verification.md").write_text("Spec of the q4j gate\n")
    for name, content in LEGACY_GATE.items():
        (template / name).parent.mkdir(parents=True, exist_ok=True)
        (template / name).write_text(content)


def validate_gate_migration(temporary: Path, static: bool) -> None:
    """A project generated with the q4j gate loses it on the update to 2.0.0, and keeps its own build files."""
    source = temporary / "legacy-source"
    source.mkdir()
    shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
    shutil.copytree(ROOT / "template", source / "template")
    shutil.copytree(ROOT / "migrations", source / "migrations")
    legacy_template(source / "template")
    init_git(source)
    commit(source, "Template with the q4j architecture gate")
    run(["git", "tag", "v1.4.0"], source)

    projects = {name: temporary / f"legacy-{name}" for name in ("plain", "log4j")}
    for name, project in projects.items():
        run_copy(str(source), project, defaults=True, vcs_ref="v1.4.0")
        assert (project / "gradle/architecture.gradle").is_file(), "the legacy fixture must carry the old gate"
        if name == "log4j":
            dependencies = project / "gradle/dependencies.gradle"
            dependencies.write_text(dependencies.read_text().replace(
                "dependencies {\n", "dependencies {\n    implementation libs.log4j.core\n"))
        init_git(project)
        commit(project, "Legacy project")

    shutil.rmtree(source / "template")
    shutil.copytree(ROOT / "template", source / "template")
    commit(source, "Template with the ArchGate plugin")
    run(["git", "tag", "v2.0.0"], source)

    for name, project in projects.items():
        build = (project / "build.gradle").read_text()
        try:
            run_update(project, defaults=True, overwrite=True, vcs_ref="v2.0.0")
        except UnsafeTemplateError:
            pass
        else:
            raise AssertionError("an update that crosses the migration must ask for --trust")
        run_update(project, defaults=True, overwrite=True, vcs_ref="v2.0.0", unsafe=True)
        for leftover in GATE_LEFTOVERS:
            assert not (project / leftover).exists(), f"the migration must remove {leftover}"
        assert (project / "build.gradle").read_text() == build.replace(
            "apply from: 'gradle/architecture.gradle'\n", ""), "update must only drop the apply line"
        catalog = (project / "gradle/libs.versions.toml").read_text()
        assert "q4j-architecture" not in catalog, catalog
        log4j = ("log4j = ", "log4j-core = ")
        if name == "log4j":
            assert all(entry in catalog for entry in log4j), "the migration must keep a library the build uses"
            assert "log4j-slf4j2-impl" not in catalog, catalog
        else:
            assert not any(entry in catalog for entry in log4j), catalog
        for added in (RULE_REGISTRY, "docs/agents/architecture-verification.md"):
            assert (project / added).is_file(), f"update must add {added}"
        commit(project, "Update to 2.0.0")
        run([sys.executable, str(ROOT / "migrations/remove_architecture_gate.py")], project)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=project, check=True,
                                capture_output=True, text=True).stdout
        assert not status, f"a second migration run must change nothing, changed:\n{status}"
    validate_customized_migration(source, temporary)
    if not static:
        run(["./gradlew", "--no-daemon", "check"], projects["plain"])


def validate_customized_migration(source: Path, temporary: Path) -> None:
    """The migration keeps what a customized build still uses, reports what it leaves, and keeps CRLF."""
    project = temporary / "legacy-customized"
    run_copy(str(source), project, defaults=True, vcs_ref="v1.4.0")
    build = project / "build.gradle"
    text = build.read_text().replace("apply from: 'gradle/architecture.gradle'",
                                     'apply from: "$rootDir/gradle/architecture.gradle"')
    text += "def gate = file('gradle/architecture.gradle')\ntasks.named('check') { dependsOn 'verifyArchitecture' }\n"
    build.write_bytes(text.replace("\n", "\r\n").encode())
    (project / "gradle/extra.gradle").write_text("apply from: file('gradle/architecture.gradle')\n")
    catalog = project / "gradle/libs.versions.toml"
    catalog.write_text(catalog.read_text().replace(
        "[plugins]\n", 'extra = { module = "org.example:extra", version = { ref = "log4j" } }\n\n[plugins]\n')
        + '\n[bundles]\nlogging = ["log4j-slf4j2-impl"]\n')
    (project / "gradle.properties").write_bytes(b"org.gradle.caching=true\r\narchitecture.packages=com.example\r\n")
    registry = project / "tools/architecture/META-INF/services/dev.quokkify.architecture.contract.ArchitectureRule"
    registry.write_text(registry.read_text() + "com.example.CustomRule\n")

    output = subprocess.run([sys.executable, str(ROOT / "migrations/remove_architecture_gate.py")], cwd=project,
                            check=True, capture_output=True, text=True).stdout
    print(output)
    built = build.read_bytes()
    assert b"architecture.gradle\"" not in built.split(b"def gate")[0], "the $rootDir apply line must go"
    assert b"\n" not in built.replace(b"\r\n", b""), "build.gradle must keep its CRLF line endings"
    assert "architecture.gradle" not in (project / "gradle/extra.gradle").read_text(), "the file() apply line must go"
    assert (project / "gradle/architecture.gradle").is_file(), "a gate script still referenced must be kept"
    assert "build.gradle:" in output and "def gate = file('gradle/architecture.gradle')" in output, output
    assert "dependsOn 'verifyArchitecture'" in output, "leftover verifyArchitecture references must be reported"
    assert "com.example.CustomRule" in output, "rules the template did not list must be reported"
    assert "ARCHITECTURE GATE IS NOW DISABLED" in output, output
    assert (project / "gradle.properties").read_bytes() == b"org.gradle.caching=true\r\n", "CRLF must stay"
    catalog_text = catalog.read_text()
    for kept in ("log4j = ", "log4j-slf4j2-impl = "):
        assert kept in catalog_text, f"{kept.strip(' =')} is still used and must be kept"
    for removed in ("q4j-architecture", "log4j-core"):
        assert removed not in catalog_text, f"{removed} is unused and must be removed"


STEP_PROBE = """package com.example.test_automation.test;

import io.qameta.allure.Step;
import org.testng.annotations.Test;

public class AllureStepProbeTest {

  @Test
  public void recordsSteps() {
    probe();
  }

  @Step("probe step")
  public void probe() {
  }
}
"""


def assert_allure_steps(project: Path) -> None:
    """Run a throwaway test with a @Step method and require the step in its Allure result."""
    probe = project / "src/test/java/com/example/test_automation/test/AllureStepProbeTest.java"
    probe.write_text(STEP_PROBE)
    try:
        run(["./gradlew", "--no-daemon", "-q", "clean", "test", "--tests", "*AllureStepProbeTest"], project)
        results = list((project / "build/allure-results").glob("*-result.json"))
        assert results, "tests must write Allure results to build/allure-results"
        steps = [step["name"] for result in results for step in json.loads(result.read_text()).get("steps", [])]
        assert "probe step" in steps, f"the AspectJ agent must weave @Step into results, found {steps}"
    finally:
        probe.unlink()


CONSOLE_PROBE = """package com.example.test_automation.step;

public final class ConsoleProbe {

  private ConsoleProbe() {
  }

  public static void print() {
    System.out.println("probe");
  }
}
"""


def assert_gate_fails_on_console_output(project: Path) -> None:
    """A System.out call in src/main must fail archgateCheck."""
    probe = project / "src/main/java/com/example/test_automation/step/ConsoleProbe.java"
    probe.write_text(CONSOLE_PROBE)
    try:
        gate = subprocess.run(["./gradlew", "--no-daemon", "--console=plain", "archgateCheck"], cwd=project,
                              capture_output=True, text=True)
        assert gate.returncode != 0, "archgateCheck must fail on System.out in main code"
        report = gate.stdout + gate.stderr
        assert "No console output" in report, report
    finally:
        probe.unlink()


STAND_PROBE = """package com.example.test_automation.seed.load;

import org.testng.annotations.Test;

public class ProbeStandTest {

  @Test
  public void changesTheStand() {
  }
}
"""


STUB_LOADER = """package com.example.test_automation.seed.load;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

import com.example.test_automation.seed.scenario.Scenario;

public class StubScenarioLoader implements ScenarioLoader {

  @Override
  public void load(Scenario scenario) {
    try {
      Files.writeString(Path.of("MARKER"), "loaded");
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }
}
"""
STUB_PROBE = """package com.example.test_automation.seed.stand;

import java.util.Map;

public class StubStandProbe implements StandProbe {

  @Override
  public Map<String, String> capture() {
    return Map.of("users", "0");
  }
}
"""
# A seed block of a guide: `{%- ... %}` also drops the newline before it, `-#}` the one after the leading comment.
SEED_BLOCK = re.compile(r"\n\{%- if with_seed_module %\}.*?\{%- endif %\}"
                        r"|\{% if with_seed_module %\}.*?\{% endif %\}|^\{#-.*?-#\}\n", re.S)


def assert_guides_unchanged_without_seed(plain: Path) -> None:
    """Without the flag, the guides are their .jinja source minus the seed blocks: nothing else is templated."""
    for guide in ("AGENTS.md", "README.md"):
        source = (ROOT / "template" / f"{guide}.jinja").read_text()
        assert (plain / guide).read_text() == SEED_BLOCK.sub("", source), f"{guide} renders differently without seed"


def assert_seed_static(project: Path, plain: Path) -> None:
    """With the flag on, seed/ is generated and wired; with it off, nothing of it is."""
    for name in SEED_EXPECTED:
        assert (project / name).is_file(), f"missing generated seed file: {name}"
        assert not (plain / name).exists(), f"{name} must not be generated without with_seed_module"
    for package in SEED_PACKAGES:
        assert (project / SEED_MAIN / package).is_dir(), package
    settings = (project / "settings.gradle").read_text()
    assert "include 'seed'" in settings and "files('seed/gradle/seed.versions.toml')" in settings, settings
    build = (project / "seed/build.gradle").read_text()
    for line in ("implementation project(':')", "seedLibs.datafaker"):
        assert line in (project / "seed/gradle/dependencies.gradle").read_text(), line
    for line in ("rootPackage = 'com.example.test_automation.seed'", "failOn = 'ERROR'",
                 "mainClass = 'com.example.test_automation.seed.cli.SeedCli'", "tasks.register('standTest', Test)"):
        assert line in build, f"seed/build.gradle must contain {line}"
    assert "sourceSets.main.output" not in build, "seed must depend on the main project, not on its source sets"
    assert re.search(r'^datafaker = "[0-9.]+"$', (project / "seed/gradle/seed.versions.toml").read_text(), re.M)
    assert "datafaker" not in (project / "gradle/libs.versions.toml").read_text(), "Datafaker is used only in seed/"
    datafaker_users = {path.name for path in (project / "seed/src").rglob("*.java") if "net.datafaker" in path.read_text()}
    assert datafaker_users == {"FakeValues.java"}, datafaker_users
    for java_file in (project / "seed/src").rglob("*.java"):
        text = java_file.read_text()
        assert not re.search(r"System\.(getProperty|getenv)|RestAssured|java\.sql|groups *=", text), java_file
    for guide in ("AGENTS.md", "README.md"):
        assert "](docs/agents/seed-module.md)" in (project / guide).read_text(), guide
        assert "seed" not in (plain / guide).read_text().lower(), f"{guide} mentions seed without the flag"
    for path in (project / "seed").rglob("*"):
        if path.is_file():
            text = path.read_text()
            assert "{%" not in text and "{{" not in text, f"unrendered template in {path}"
    assert (plain / "settings.gradle").read_text() == 'rootProject.name = "test-automation"\n'
    assert_guides_unchanged_without_seed(plain)
    root_build = (project / "build.gradle").read_text()
    for plugin in ("alias(libs.plugins.spotbugs)", "alias(libs.plugins.archgate)"):
        assert plugin in root_build, f"seed/build.gradle applies {plugin} by id, so the root build must apply it"
    for library in ("testng", "checkstyle", "archgate-bom"):
        assert re.search(rf"^{library} = ", (project / "gradle/libs.versions.toml").read_text(), re.M), library
    versions = [re.search(r'^q4j = "([^"]+)"$', (project / name).read_text(), re.M).group(1)
                for name in ("gradle/libs.versions.toml", "seed/gradle/seed.versions.toml")]
    assert versions[0] == versions[1], f"the q4j versions of both catalogs must match: {versions}"


def assert_seed_gradle(project: Path) -> None:
    """check runs the seed unit tests and gate, generate is repeatable, standTest runs only *StandTest."""
    planned = subprocess.run(["./gradlew", "--no-daemon", "-q", "check", "--dry-run"], cwd=project,
                             check=True, capture_output=True, text=True).stdout
    for task in (":seed:test", ":seed:archgateCheck", ":seed:checkstyleMain", ":seed:spotbugsMain"):
        assert task in planned, f"check must run {task}"
    assert ":seed:standTest" not in planned, "check must not run standTest"
    run(["./gradlew", "--no-daemon", "check"], project)
    outputs = []
    for name in ("first", "second"):
        out = project / "seed/build" / name
        run(["./gradlew", "--no-daemon", "-q", ":seed:run", f"--args=generate --seed 1 --dir build/{name}"], project)
        outputs.append(snapshot(out))
    assert outputs[0] == outputs[1] and outputs[0], "generate --seed 1 must write identical files"
    golden = (project / "seed/src/test/resources/golden/scenario-seed-1-small.json").read_bytes()
    assert outputs[0][Path("scenario.json")] == golden, "generate --seed 1 must match the golden scenario"
    assert_registered_extensions_stay_unused(project)
    probe = project / SEED_TEST / "load/ProbeStandTest.java"
    probe.write_text(STAND_PROBE)
    try:
        for task, expected in ((":seed:test", False), (":seed:standTest", True)):
            output = subprocess.run(["./gradlew", "--no-daemon", "--console=plain", task, "--rerun"], cwd=project,
                                    check=True, capture_output=True, text=True).stdout
            assert ("ProbeStandTest > changesTheStand PASSED" in output) == expected, f"{task}:\n{output}"
            assert expected or "SeedCliTest" in output, f"{task} must run the unit tests:\n{output}"
    finally:
        probe.unlink()


def assert_registered_extensions_stay_unused(project: Path) -> None:
    """Registered ScenarioLoader/StandProbe and data in the default dir must not make :seed:test call them."""
    marker = project / "seed/MARKER"
    stubs = {
        f"{SEED_MAIN}/load/StubScenarioLoader.java": STUB_LOADER,
        f"{SEED_MAIN}/stand/StubStandProbe.java": STUB_PROBE,
        "seed/src/main/resources/META-INF/services/com.example.test_automation.seed.load.ScenarioLoader":
            "com.example.test_automation.seed.load.StubScenarioLoader\n",
        "seed/src/main/resources/META-INF/services/com.example.test_automation.seed.stand.StandProbe":
            "com.example.test_automation.seed.stand.StubStandProbe\n",
    }
    for name, content in stubs.items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text(content)
    try:
        run(["./gradlew", "--no-daemon", "-q", ":seed:run", "--args=generate --seed 1"], project)
        run(["./gradlew", "--no-daemon", "-q", ":seed:run", "--args=load"], project)
        assert marker.is_file(), "the stub loader must work when the command line calls it"
        marker.unlink()
        run(["./gradlew", "--no-daemon", ":seed:test", "--rerun"], project)
        assert not marker.exists(), ":seed:test must not call a registered ScenarioLoader"
    finally:
        for name in stubs:
            (project / name).unlink()
        marker.unlink(missing_ok=True)


def validate(static: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="java-test-automation-template-") as tmp:
        temporary = Path(tmp).resolve()
        source = temporary / "source"
        source.mkdir()
        shutil.copy2(ROOT / "copier.yml", source / "copier.yml")
        shutil.copytree(ROOT / "template", source / "template")
        init_git(source)
        commit(source, "Current working template")
        # Tagged with the latest migration's version, so the ownership update below runs no migration.
        run(["git", "tag", "v2.0.0"], source)

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
        assert not (project / "gradle.properties").exists(), "the template no longer renders gradle.properties"
        build = (project / "build.gradle").read_text()
        assert "alias(libs.plugins.archgate)" in build, build
        assert "rootPackage = 'com.example.test_automation'" in build, build
        assert "failOn = 'ERROR'" in build, build
        catalog = (project / "gradle/libs.versions.toml").read_text()
        for entry in (r'^archgate = "[0-9.]+"$', r'^archgate-bom = .*"dev\.quokkify\.archgate:archgate-bom"',
                      r'^archgate = \{ id = "dev\.quokkify\.archgate"'):
            assert re.search(entry, catalog, re.M), f"catalog must match {entry}"
        dependencies = (project / "gradle/dependencies.gradle").read_text()
        for line in ("testImplementation platform(libs.archgate.bom)",
                     "testImplementation 'dev.quokkify.archgate:archgate-rules-archunit'"):
            assert line in dependencies, f"dependencies.gradle must declare {line}"
        registry = project / RULE_REGISTRY
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
            assert "](docs/agents/test-reporting.md)" in text, guide
            assert "](docs/agents/architecture-verification.md)" in text, guide
        assert "apply from: 'gradle/allure.gradle'" in (project / "build.gradle").read_text()
        assert re.search(r"^aspectj-weaver = ", catalog, re.M), "catalog must declare aspectj-weaver"
        assert "allure-results/" in (project / ".gitignore").read_text().split()
        answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
        assert answers["project_name"] == "test-automation", answers
        assert answers["_src_path"], "answers must record the template source"
        assert answers["package_root"] == "com.example", answers
        assert answers["package_name"] == "test_automation", answers
        starter = project / "src/test/java/com/example/test_automation/test/StarterTest.java"
        assert starter.read_text().startswith("package com.example.test_automation.test;"), starter

        seeded = temporary / "seeded"
        run_copy(str(source), seeded, data={"with_seed_module": True}, defaults=True, vcs_ref="HEAD")
        assert_seed_static(seeded, project)

        named = temporary / "named"
        run_copy(str(source), named, data={"project_name": "qa.suite"}, defaults=True, vcs_ref="HEAD")
        assert 'rootProject.name = "qa.suite"' in (named / "settings.gradle").read_text()
        assert (named / "src/main/java/com/example/qa_suite/step/BaseSteps.java").is_file()
        digits = temporary / "digits"
        run_copy(str(source), digits, data={"project_name": "123-app"}, defaults=True, vcs_ref="HEAD")
        assert (digits / "src/main/java/com/example/p_123_app/step/BaseSteps.java").is_file()
        custom = temporary / "custom"
        run_copy(str(source), custom, data={"package_root": "dev.quokkify", "package_name": "marketdesk",
                                            "with_seed_module": True}, defaults=True, vcs_ref="HEAD")
        base_steps = custom / "src/main/java/dev/quokkify/marketdesk/step/BaseSteps.java"
        assert base_steps.read_text().startswith("package dev.quokkify.marketdesk.step;"), base_steps
        assert "rootPackage = 'dev.quokkify.marketdesk'" in (custom / "build.gradle").read_text()
        assert "rootPackage = 'dev.quokkify.marketdesk.seed'" in (custom / "seed/build.gradle").read_text()
        # Checkstyle's CustomImportOrder puts dev.quokkify in its own group and sorts other third-party
        # imports together, so the starter imports depend on the base package.
        late = temporary / "late"
        run_copy(str(source), late, data={"package_root": "org.zeta", "package_name": "suite",
                                          "with_seed_module": True}, defaults=True, vcs_ref="HEAD")
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
            assert_allure_steps(project)
            planned = subprocess.run(["./gradlew", "--no-daemon", "-q", "check", "--dry-run"], cwd=project,
                                     check=True, capture_output=True, text=True).stdout
            assert ":archgateCheck" in planned, "check must run archgateCheck"
            assert_gate_fails_on_console_output(project)
            assert_seed_gradle(seeded)
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
        for directory in (".gradle", "build", "seed/.gradle", "seed/build"):
            shutil.rmtree(seeded / directory, ignore_errors=True)
        init_git(seeded)
        seed_markers: dict[str, bytes] = {}
        for path in seeded.rglob("*"):
            name = path.relative_to(seeded).as_posix()
            if path.is_file() and ".git" not in path.relative_to(seeded).parts and name not in MANAGED | SEED_MANAGED:
                path.write_bytes(b"project-owned fixture content\n")
                seed_markers[name] = b"project-owned fixture content\n"
        assert "seed/gradle/dependencies.gradle" in seed_markers and "settings.gradle" in seed_markers
        commit(seeded, "Project customization")

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
        for name in SEED_MANAGED:
            assert not (project / name).exists(), f"update must not add {name} without with_seed_module"
        run_update(seeded, defaults=True, overwrite=True, vcs_ref="v9.9.9")
        for name, marker in seed_markers.items():
            assert (seeded / name).read_bytes() == marker, f"update replaced {name}"
        for name in SEED_MANAGED | {"AGENTS.md", "README.md"}:
            text = (seeded / name).read_text()
            assert "Updated template fixture content" in text, f"{name} must be refreshed by update"
            assert "{{" not in text and "{%" not in text, f"unrendered template in {name}"
        assert "rootPackage = 'com.example.test_automation.seed'" in (seeded / "seed/build.gradle").read_text()
        assert "with_seed_module: true" in (seeded / ".copier-answers.yml").read_text().splitlines()
        validate_gate_migration(temporary, static)
    print("java-test-automation-template validation: OK" + (" (static)" if static else " (with Gradle)"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="skip the Gradle build")
    validate(parser.parse_args().static)
