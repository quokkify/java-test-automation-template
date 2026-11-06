# java-test-automation-template

Copier template for a Java 21 test automation project: Gradle, TestNG, [q4j](https://github.com/quokkify/q4j) configuration, Checkstyle, and SpotBugs.

## Use it

Prerequisites:

- [ ] `git`
- [ ] `gh`, authenticated (`gh auth login`, then `gh auth setup-git` so Copier can clone over HTTPS)
- [ ] Copier >= 9.18.2 (`uv tool install copier` or `pipx install copier`)

From your repository root:

```sh
copier copy --vcs-ref "$(gh release view --repo quokkify/java-test-automation-template --json tagName --jq .tagName)" gh:quokkify/java-test-automation-template test-automation
```

Result:

```text
test-automation/
  .copier-answers.yml
  .gitattributes
  .gitignore
  README.md
  AGENTS.md      (agent rules: layout, config, q4j docs)
  build.gradle
  settings.gradle
  gradlew, gradlew.bat
  gradle/        (scripts, version catalog, wrapper)
  src/main/java/<root>/<name>/   config, model, service, helper, verification, step (BaseSteps)
  src/test/java/<root>/<name>/   test (BaseTest, StarterTest)
  tools/         (Checkstyle, SpotBugs)
```

Copier asks for `project_name`, `package_root` (e.g. `dev.quokkify`), `package_name` (defaults to the project name), and `with_seed_module` (default `false`). Everything except `README.md`, `AGENTS.md` and the specs under `docs/agents/` is yours after creation; `copier update` refreshes those. See the generated README.

### Optional seed module

`with_seed_module=true` adds `seed/`, a Gradle subproject for synthetic test data: a deterministic Datafaker generator with size presets, a loader and stand checkpoints behind extension points, and a `generate`/`load`/`diff` command line. It depends on the main project, so it reuses its configs, services and steps. `./gradlew check` runs its unit tests and architecture gate; tests that change the stand are `*StandTest` classes run by `./gradlew :seed:standTest`. `copier update` replaces `seed/build.gradle`; seed dependencies and sources stay yours. The layout and rules are in the generated `docs/agents/seed-module.md`.

```sh
copier copy --data with_seed_module=true --vcs-ref "<tag>" gh:quokkify/java-test-automation-template test-automation
```

## Update

From inside the generated folder:

```sh
copier update --vcs-ref "$(gh release view --repo quokkify/java-test-automation-template --json tagName --jq .tagName)"
```

An update across a release with a Copier migration stops and asks for `--trust`. Add the option to run the
migration; the script lives in `migrations/` of this repository. The 2.0.0 migration removes the q4j
architecture gate; then follow section 3 of the generated `docs/agents/architecture-verification.md` to
enable the ArchGate plugin that replaces it.

## Develop the template

```sh
pip install PyYAML==6.0.3 copier==9.18.2
python scripts/validate.py --static   # render, ownership, update checks
python scripts/validate.py            # also runs Gradle (needs JDK 21)
```
