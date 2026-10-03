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
  build.gradle
  settings.gradle
  gradlew, gradlew.bat
  gradle/        (scripts, version catalog, wrapper)
  src/test/      (example test and config)
  tools/         (Checkstyle, SpotBugs)
```

Everything except `README.md` is yours after creation; see the generated README.

## Update

From inside the generated folder:

```sh
copier update --vcs-ref "$(gh release view --repo quokkify/java-test-automation-template --json tagName --jq .tagName)"
```

## Develop the template

```sh
pip install PyYAML==6.0.3 copier==9.18.2
python scripts/validate.py --static   # render, ownership, update checks
python scripts/validate.py            # also runs Gradle (needs JDK 21)
```
